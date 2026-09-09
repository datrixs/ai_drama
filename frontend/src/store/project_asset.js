import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as assetsApi from '@/api/project/assets'
import { downloadImageUrl, sanitizeFilename } from '@/utils/download'
import { directUpload, directUploadWithThumbnail } from '@/utils/cosUpload'

export const useProjectAssetStore = defineStore('projectAsset', () => {
  const characters = ref([])
  const locations = ref([])
  const props = ref([])
  const stats = ref({ total: 0, pending: 0, generating: 0, completed: 0, failed: 0 })
  const allReady = ref(false)
  const kindFilter = ref('all')
  const loading = ref(false)
  const isParsing = ref(false)
  const isBatchGenerating = ref(false)
  const volcSyncingIds = ref(new Set())
  // 正在上传图片的资产 ID 集合（前端临时状态，用于卡片显示上传中占位）
  const uploadingIds = ref([])

  // ============ 批量同步状态（对齐资产中心交互） ============
  // 确认后 → 后端 started 事件到达之间的防抖标记
  const batchSyncPending = ref(false)
  // 整体进度：总数 + 已完成数
  const batchSyncTotal = ref(0)
  const batchSyncDone = ref(0)
  // 正在同步的资产 ID 集合
  const batchSyncingAssetIds = ref(new Set())

  const isBatchSyncing = computed(
    () => batchSyncPending.value || batchSyncTotal.value > 0,
  )

  // ============ 获取资产 ============

  async function fetchAssets(projectId, type = 'all') {
    loading.value = true
    try {
      const res = await assetsApi.getAssets(projectId, type)
      characters.value = res.characters || []
      locations.value = res.locations || []
      props.value = res.props || []
      stats.value = res.stats || { total: 0, pending: 0, generating: 0, completed: 0, failed: 0 }
      allReady.value = res.all_ready || false
    } catch {
      // 错误提示由 request 拦截器统一处理
    } finally {
      loading.value = false
    }
  }

  // ============ 解析资产 ============

  async function parseAssets(projectId) {
    isParsing.value = true
    try {
      await assetsApi.parseAssets(projectId)
      await fetchAssets(projectId)
      ElMessage.success('资产解析完成')
    } catch (e) {
      throw e
    } finally {
      isParsing.value = false
    }
  }

  // ============ 图片生成 ============

  async function generateSingle(projectId, assetType, assetId) {
    const list = _getListRef(assetType)
    const item = list?.value.find(a => a.id === assetId)
    const prevStatus = item?.gen_status
    _updateLocalStatus(assetType, assetId, 'generating')
    try {
      await assetsApi.generateAssetImage(projectId, assetType, assetId)
    } catch {
      _updateLocalStatus(assetType, assetId, prevStatus || 'pending')
    }
  }

  async function batchGenerate(projectId) {
    isBatchGenerating.value = true

    // 收集待更新资产（与后端 get_all_pending 过滤一致）
    const targets = []
    for (const type of ['character', 'location', 'prop']) {
      const list = _getListRef(type)
      if (list) {
        for (const a of list.value) {
          if (a.gen_status !== 'completed') {
            targets.push({ type, id: a.id, prevStatus: a.gen_status })
          }
        }
      }
    }

    // 乐观更新：立即显示生成中
    for (const t of targets) {
      _updateLocalStatus(t.type, t.id, 'generating')
    }

    try {
      const res = await assetsApi.batchGenerate(projectId)
      if (res?.total > 0) {
        ElMessage.success(`已提交 ${res.total} 个资产生成任务`)
      } else {
        // 后端说没有需要生成的资产，回滚
        for (const t of targets) {
          _updateLocalStatus(t.type, t.id, t.prevStatus)
        }
        ElMessage.info('没有需要生成的资产')
      }
    } catch {
      for (const t of targets) {
        _updateLocalStatus(t.type, t.id, t.prevStatus)
      }
    } finally {
      isBatchGenerating.value = false
    }
  }

  // ============ 编辑 ============

  async function updateAsset(projectId, assetType, assetId, data) {
    try {
      const res = await assetsApi.updateAsset(projectId, assetType, assetId, data)
      _updateLocalAsset(assetType, assetId, res)
      return res
    } catch (e) {
      throw e
    }
  }

  async function deleteAsset(projectId, assetType, assetId) {
    try {
      await assetsApi.deleteAsset(projectId, assetType, assetId)
      _removeLocalAsset(assetType, assetId)
      ElMessage.success('删除成功')
    } catch (e) {
      // 错误提示由 request 拦截器统一提示
    }
  }

  // ============ 图片上传 ============

  async function uploadImage(projectId, assetType, assetId, file, { silent = false } = {}) {
    uploadingIds.value = [...uploadingIds.value, assetId]
    try {
      const { cos_key, thumbnail_cos_key } = await directUploadWithThumbnail(file, { category: 'upload', biz: `project-${assetType}` })
      const res = await assetsApi.confirmAssetImage(projectId, assetType, assetId, cos_key, thumbnail_cos_key)
      _updateLocalImage(assetType, assetId, res)
      if (!silent) {
        if (res?.sync_error) ElMessage.warning(`资产已上传，但资产库同步失败：${res.sync_error}`)
        else ElMessage.success('图片上传成功')
      }
      return res
    } catch (e) {
      // 错误提示由 request 拦截器统一处理
      throw e
    } finally {
      uploadingIds.value = uploadingIds.value.filter(id => id !== assetId)
    }
  }

  // ============ AI 修图 ============

  async function modifyImage(projectId, assetType, assetId, data) {
    const list = _getListRef(assetType)
    const item = list?.value.find(a => a.id === assetId)
    const prevStatus = item?.gen_status
    _updateLocalStatus(assetType, assetId, 'generating')
    try {
      await assetsApi.modifyAssetImage(projectId, assetType, assetId, data)
    } catch {
      _updateLocalStatus(assetType, assetId, prevStatus || 'pending')
    }
  }

  // ============ 参考图生图 ============

  async function referenceGenerate(projectId, assetId, data) {
    const list = _getListRef('character')
    const item = list?.value.find(a => a.id === assetId)
    const prevStatus = item?.gen_status
    _updateLocalStatus('character', assetId, 'generating')
    try {
      await assetsApi.referenceGenerateCharacter(projectId, assetId, data)
    } catch {
      _updateLocalStatus('character', assetId, prevStatus || 'pending')
    }
  }

  // ============ 提取描述 ============

  async function extractDescription(projectId, data) {
    try {
      const res = await assetsApi.extractCharacterDescription(projectId, data)
      return res?.description || ''
    } catch {
      return ''
    }
  }

  // ============ AI 修改描述 ============

  async function aiModifyDescription(projectId, assetType, assetId, data) {
    try {
      const res = await assetsApi.aiModifyDescription(projectId, assetType, assetId, data)
      return res?.description || ''
    } catch {
      return ''
    }
  }

  // ============ 下载 ============

  async function downloadAssetImage(asset) {
    if (!asset.image_url) return
    const filename = sanitizeFilename(asset.name || 'asset') + '.jpg'
    await downloadImageUrl(asset.image_url, filename)
  }

  async function batchDownload(projectId) {
    try {
      const token = localStorage.getItem('token')
      const url = `/api/v1/projects/${projectId}/assets/download`
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      if (!resp.ok) {
        if (resp.status === 404) {
          ElMessage.info('没有可下载的图片')
          return
        }
        throw new Error('下载失败')
      }
      const blob = await resp.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      const disposition = resp.headers.get('Content-Disposition')
      const match = disposition?.match(/filename="?([^"]+)"?/)
      a.download = match?.[1] || `project-assets_${new Date().toISOString().slice(0, 10)}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(a.href)
    } catch {
      ElMessage.error('批量下载失败')
    }
  }

  // ============ WebSocket 更新方法 ============

  function updateAssetImage(assetType, assetId, imageUrl, thumbnailUrl) {
    const list = _getListRef(assetType)
    if (!list) return
    const item = list.value.find(a => a.id === assetId)
    if (item) {
      if (item.image_url) {
        item.previous_image_url = item.image_url
      }
      item.image_url = imageUrl
      if (thumbnailUrl !== undefined) {
        item.thumbnail_url = thumbnailUrl
      }
      item.gen_status = 'completed'
      item.volc_private_asset_id = null
    }
    _refreshStats()
  }

  function updateAssetStatus(assetType, assetId, status) {
    const list = _getListRef(assetType)
    if (!list) return
    const item = list.value.find(a => a.id === assetId)
    if (item) {
      item.gen_status = status
    }
    _refreshStats()
  }

  // ============ 火山私域同步 ============

  async function syncToVolc(projectId, assetType, assetId) {
    volcSyncingIds.value.add(assetId)
    try {
      const { syncAssetToVolc } = await import('@/api/project/asset')
      const assetKind = assetType === 'location' ? 'scene' : assetType
      const res = await syncAssetToVolc(projectId, assetId, assetKind)
      if (res?.volc_private_asset_id) {
        _updateVolcId(assetType, assetId, res.volc_private_asset_id)
      }
    } catch {
      // 同步失败，volc_private_asset_id 保持为空，卡片显示重试按钮
    } finally {
      volcSyncingIds.value.delete(assetId)
    }
  }

  // ============ 批量同步状态管理（对齐资产中心交互） ============

  function markBatchSyncPending(total = 0, assetIds = []) {
    batchSyncPending.value = true
    // 允许调用方在确认同步时就预置已知待同步资产，使卡片立即显示"同步中"角标
    // 不必等待后端 WS started 事件到达
    if (assetIds.length) {
      batchSyncTotal.value = Number(total) || assetIds.length
      batchSyncDone.value = 0
      batchSyncingAssetIds.value = new Set(assetIds)
    }
  }

  function markBatchSyncStarted(total, assetIds = []) {
    batchSyncTotal.value = Number(total) || (assetIds || []).length
    batchSyncDone.value = 0
    // 创建新 Set 触发响应式更新（原地 add/delete 在某些场景下不触发）
    batchSyncingAssetIds.value = new Set(assetIds || [])
    batchSyncPending.value = false
  }

  function setAssetBatchSyncing(assetId, isSyncing) {
    // 复制后修改再赋值，保证响应式更新（与资产中心实现一致）
    const next = new Set(batchSyncingAssetIds.value)
    if (isSyncing) next.add(assetId); else next.delete(assetId)
    batchSyncingAssetIds.value = next
  }

  function isAssetBatchSyncing(assetId) {
    return batchSyncingAssetIds.value.has(assetId)
  }

  function incBatchSyncDone() {
    batchSyncDone.value += 1
  }

  function resetBatchSync() {
    batchSyncPending.value = false
    batchSyncTotal.value = 0
    batchSyncDone.value = 0
    batchSyncingAssetIds.value = new Set()
  }

  // 批量同步项目所有未同步资产到火山/BytePlus（后端异步 Celery 任务，按 region 自动判断）
  async function batchSyncVolc(projectId) {
    try {
      await assetsApi.batchSyncProjectAssets(projectId)
      ElMessage.success('批量同步任务已开始')
    } catch {
      // 失败时回滚 pending 状态，让按钮可重新点击
      resetBatchSync()
    }
  }

  function updateVolcSyncStatus(assetType, assetId, volcPrivateAssetId) {
    _updateVolcId(assetType, assetId, volcPrivateAssetId)
    volcSyncingIds.value.delete(assetId)
  }

  function _updateVolcId(assetType, assetId, volcId) {
    const list = _getListRef(assetType)
    if (!list) return
    const item = list.value.find(a => a.id === assetId)
    if (item) {
      item.volc_private_asset_id = volcId
    }
  }

  // ============ 从资产中心导入 ============

  async function copyFromGlobal(projectId, assetType, assetId, globalAssetId, { silent = false } = {}) {
    try {
      const res = await assetsApi.copyFromGlobal(projectId, assetType, assetId, globalAssetId)
      _updateLocalAsset(assetType, assetId, res)
      if (!silent) ElMessage.success('导入成功')
      return res
    } catch (e) {
      throw e
    }
  }

  // ============ 创建资产 ============

  async function createAsset(projectId, assetType, data, { silent = false } = {}) {
    try {
      const res = await assetsApi.createAsset(projectId, assetType, data)
      const list = _getListRef(assetType)
      if (list) {
        list.value.push(res)
      }
      _refreshStats()
      if (!silent) ElMessage.success('创建成功')
      return res
    } catch (e) {
      throw e
    }
  }

  // ============ 撤销图片 ============

  async function undoImage(projectId, assetType, assetId) {
    try {
      const res = await assetsApi.undoImage(projectId, assetType, assetId)
      _updateLocalAsset(assetType, assetId, res)
      ElMessage.success('已撤销到上一版本')
      return res
    } catch {
      // 错误提示由 request 拦截器统一处理
    }
  }

  // ============ 音色 ============

  async function uploadCharacterVoice(projectId, assetId, file) {
    try {
      const res = await assetsApi.uploadCharacterVoice(projectId, assetId, file)
      _updateLocalAsset('character', assetId, res)
      return res
    } catch (e) {
      throw e
    }
  }

  async function bindVoice(projectId, assetId, voiceData) {
    try {
      const res = await assetsApi.updateAsset(projectId, 'character', assetId, {
        voice_id: voiceData.voice_id || null,
        voice_type: voiceData.voice_type || null,
        custom_voice_url: voiceData.custom_voice_url || null,
      })
      _updateLocalAsset('character', assetId, res)
      ElMessage.success('音色设置成功')
      return res
    } catch (e) {
      throw e
    }
  }

  // ============ 内部辅助 ============

  function _getListRef(assetType) {
    if (assetType === 'character') return characters
    if (assetType === 'location') return locations
    if (assetType === 'prop') return props
    return null
  }

  function _updateLocalStatus(assetType, assetId, status) {
    const list = _getListRef(assetType)
    if (!list) return
    const item = list.value.find(a => a.id === assetId)
    if (item) {
      item.gen_status = status
    }
    _refreshStats()
  }

  function _updateLocalImage(assetType, assetId, payload) {
    const list = _getListRef(assetType)
    if (!list) return
    const item = list.value.find(a => a.id === assetId)
    if (!item) return
    // payload 是后端 upload_image 返回的对象（包含 image_url/thumbnail_url/volc_private_asset_id/byteplus_asset_id）
    if (item.image_url && payload.image_url && item.image_url !== payload.image_url) {
      item.previous_image_url = item.image_url
    }
    if (payload.image_url !== undefined) item.image_url = payload.image_url
    if (payload.thumbnail_url !== undefined) item.thumbnail_url = payload.thumbnail_url
    if (payload.volc_private_asset_id !== undefined) item.volc_private_asset_id = payload.volc_private_asset_id
    if (payload.byteplus_asset_id !== undefined) item.byteplus_asset_id = payload.byteplus_asset_id
    item.gen_status = 'completed'
  }

  function _updateLocalAsset(assetType, assetId, data) {
    const list = _getListRef(assetType)
    if (!list) return
    const idx = list.value.findIndex(a => a.id === assetId)
    if (idx >= 0 && data) {
      list.value[idx] = { ...list.value[idx], ...data }
    }
  }

  function _removeLocalAsset(assetType, assetId) {
    const list = _getListRef(assetType)
    if (!list) return
    list.value = list.value.filter(a => a.id !== assetId)
    _refreshStats()
  }

  function _refreshStats() {
    const total = characters.value.length + locations.value.length + props.value.length
    const pending = [...characters.value, ...locations.value, ...props.value].filter(a => a.gen_status === 'pending').length
    const generating = [...characters.value, ...locations.value, ...props.value].filter(a => a.gen_status === 'generating').length
    const completed = [...characters.value, ...locations.value, ...props.value].filter(a => a.gen_status === 'completed').length
    const failed = [...characters.value, ...locations.value, ...props.value].filter(a => a.gen_status === 'failed').length
    stats.value = { total, pending, generating, completed, failed }
    allReady.value = total > 0 && pending === 0 && generating === 0 && failed === 0
  }

  function reset() {
    characters.value = []
    locations.value = []
    props.value = []
    stats.value = { total: 0, pending: 0, generating: 0, completed: 0, failed: 0 }
    allReady.value = false
    kindFilter.value = 'all'
    loading.value = false
    isParsing.value = false
    isBatchGenerating.value = false
  }

  return {
    characters, locations, props, stats, allReady,
    kindFilter, loading, isParsing, isBatchGenerating, volcSyncingIds, uploadingIds,
    batchSyncPending, batchSyncTotal, batchSyncDone, batchSyncingAssetIds, isBatchSyncing,
    markBatchSyncPending, markBatchSyncStarted, setAssetBatchSyncing, isAssetBatchSyncing, incBatchSyncDone, resetBatchSync,
    fetchAssets, parseAssets,
    generateSingle, batchGenerate,
    updateAsset, deleteAsset,
    uploadImage, modifyImage,
    referenceGenerate, extractDescription, aiModifyDescription,
    downloadAssetImage, batchDownload,
    updateAssetImage, updateAssetStatus,
    syncToVolc, batchSyncVolc, updateVolcSyncStatus,
    copyFromGlobal,
    createAsset, undoImage,
    uploadCharacterVoice, bindVoice,
    reset,
  }
})
