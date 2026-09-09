import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import * as folderApi from '@/api/asset/folder'
import * as characterApi from '@/api/asset/character'
import * as appearanceApi from '@/api/asset/appearance'
import * as locationApi from '@/api/asset/location'
import * as locationImageApi from '@/api/asset/locationImage'
import * as voiceApi from '@/api/asset/voice'
import * as locationAiApi from '@/api/asset/locationAi'
import * as characterAiApi from '@/api/asset/characterAi'
import { directUpload, directUploadWithThumbnail } from '@/utils/cosUpload'

// 纯前端虚拟标识，代表“未分组”（对应后端 folder_id IS NULL）
export const UNGROUPED_FOLDER_ID = 'ungrouped'
// 平台资产哨兵：sidebar 底部独立区域，后端按 is_management_asset=True 过滤
export const PLATFORM_FOLDER_ID = 'platform'

export const useAssetHubStore = defineStore('assetHub', () => {
  const selectedFolderId = ref(null)
  const filter = ref('all')
  const loading = ref(false)

  const folders = ref([])
  const characters = ref([])
  const locations = ref([])
  const voices = ref([])

  const sectionPage = ref({
    character: 1,
    location: 1,
    prop: 1,
    voice: 1
  })
  const pageSize = 40

  const sectionPagination = ref({
    character: { total_count: 0 },
    location: { total_count: 0 },
    prop: { total_count: 0 },
    voice: { total_count: 0 }
  })

  const props = ref([])

  function _extractData(res) {
    if (Array.isArray(res)) return res
    if (res?.data !== undefined) return res.data
    return res
  }

  function _extractPaginated(res) {
    if (res && typeof res === 'object' && 'pagination' in res && res.pagination) {
      return { data: res.data, pagination: res.pagination }
    }
    return { data: _extractData(res), pagination: null }
  }

  // 把 selectedFolderId 状态映射为后端查询参数：
  //   null(全部) → 不传
  //   'ungrouped'(未分组) → 'null' 哨兵
  //   'platform'(平台资产) → 'platform' 哨兵，后端按 is_management_asset=True 过滤
  //   其他真实 id → 原样
  function resolveFolderIdParam() {
    const id = selectedFolderId.value
    if (id === UNGROUPED_FOLDER_ID) return 'null'
    if (id === PLATFORM_FOLDER_ID) return 'platform'
    if (id) return id
    return null
  }

  async function fetchFolders() {
    const res = await folderApi.getFolderList({ is_paginate: false })
    folders.value = _extractData(res)
  }

  async function fetchCharacters() {
    const params = { page: sectionPage.value.character, size: pageSize }
    const folderId = resolveFolderIdParam()
    if (folderId) params.folder_id = folderId
    const res = await characterApi.getCharacterList(params)
    const { data, pagination } = _extractPaginated(res)
    characters.value = data
    if (pagination) sectionPagination.value.character = pagination
  }

  async function fetchLocations() {
    const params = { page: sectionPage.value.location, size: pageSize, asset_kind: 'location' }
    const folderId = resolveFolderIdParam()
    if (folderId) params.folder_id = folderId
    const res = await locationApi.getLocationList(params)
    const { data, pagination } = _extractPaginated(res)
    locations.value = data
    if (pagination) sectionPagination.value.location = pagination
  }

  async function fetchProps() {
    const params = { page: sectionPage.value.prop, size: pageSize, asset_kind: 'prop' }
    const folderId = resolveFolderIdParam()
    if (folderId) params.folder_id = folderId
    const res = await locationApi.getLocationList(params)
    const { data, pagination } = _extractPaginated(res)
    props.value = data
    if (pagination) sectionPagination.value.prop = pagination
  }

  async function fetchVoices() {
    const params = { page: sectionPage.value.voice, size: pageSize }
    const folderId = resolveFolderIdParam()
    if (folderId) params.folder_id = folderId
    const res = await voiceApi.getVoiceList(params)
    const { data, pagination } = _extractPaginated(res)
    voices.value = data
    if (pagination) sectionPagination.value.voice = pagination
  }

  async function fetchAll() {
    loading.value = true
    try {
      await Promise.all([fetchFolders(), fetchCharacters(), fetchLocations(), fetchProps(), fetchVoices()])
    } finally {
      loading.value = false
    }
  }

  // ==================== WS 驱动的状态更新 ====================

  function updateAppearanceStatus(targetId, genStatus, actionType) {
    for (const char of characters.value) {
      const app = (char.appearances || []).find(a => a.id === targetId)
      if (app) {
        app.gen_status = genStatus
        if (actionType) app.action_type = actionType
        return
      }
    }
  }

  function updateLocationImageStatus(targetId, genStatus, actionType) {
    for (const loc of [...locations.value, ...props.value]) {
      const img = (loc.images || []).find(i => i.id === targetId)
      if (img) {
        img.gen_status = genStatus
        if (actionType) img.action_type = actionType
        return
      }
    }
  }

  // 即时回写同步后的火山资产ID（避免等下次 fetch 才更新角标）
  // 注：后端按 region 写入 volc_private_asset_id 或 byteplus_asset_id；
  // 前端只更新 volc_private_asset_id（卡片组件同时判断两个字段，能正确识别已同步状态）
  function updateAppearanceVolcId(targetId, volcId) {
    for (const char of characters.value) {
      const app = (char.appearances || []).find(a => a.id === targetId)
      if (app) {
        app.volc_private_asset_id = volcId
        return
      }
    }
  }

  function updateLocationImageVolcId(targetId, volcId) {
    for (const loc of [...locations.value, ...props.value]) {
      const img = (loc.images || []).find(i => i.id === targetId)
      if (img) {
        img.volc_private_asset_id = volcId
        return
      }
    }
  }

  function updateVoiceVolcId(targetId, volcId) {
    const v = voices.value.find(x => x.id === targetId)
    if (v) v.volc_private_asset_id = volcId
  }

  function updateAppearanceImage(targetId, imageUrl, thumbnailUrl) {
    for (const char of characters.value) {
      const app = (char.appearances || []).find(a => a.id === targetId)
      if (app) {
        app.image_url = imageUrl
        if (thumbnailUrl !== undefined) {
          app.thumbnail_url = thumbnailUrl
        }
        app.gen_status = 'completed'
        app.action_type = null
        return
      }
    }
  }

  function updateLocationImageState(targetId, imageUrl, thumbnailUrl) {
    for (const loc of [...locations.value, ...props.value]) {
      const img = (loc.images || []).find(i => i.id === targetId)
      if (img) {
        img.image_url = imageUrl
        if (thumbnailUrl !== undefined) {
          img.thumbnail_url = thumbnailUrl
        }
        img.gen_status = 'completed'
        img.action_type = null
        return
      }
    }
  }

  async function selectFolder(folderId) {
    selectedFolderId.value = folderId
    sectionPage.value = { character: 1, location: 1, prop: 1, voice: 1 }
    await Promise.all([fetchCharacters(), fetchLocations(), fetchProps(), fetchVoices()])
  }

  async function createFolder(name) {
    const res = await folderApi.createFolder({ name })
    await fetchFolders()
    return _extractData(res)
  }

  async function updateFolder(folderId, name) {
    const res = await folderApi.updateFolder(folderId, { name })
    await fetchFolders()
    return _extractData(res)
  }

  async function deleteFolder(folderId) {
    await folderApi.deleteFolder(folderId)
    if (selectedFolderId.value === folderId) {
      selectedFolderId.value = null
    }
    await Promise.all([fetchFolders(), fetchCharacters(), fetchLocations(), fetchProps(), fetchVoices()])
  }

  async function createCharacter(data, { silent = false } = {}) {
    const res = await characterApi.createCharacter(data)
    // 参考图模式创建后不刷新列表（后台任务还在生成图片）
    if (!silent && !data.generate_from_reference) {
      await fetchCharacters()
    }
    return _extractData(res)
  }

  async function generateCharacterImage({ characterId, artStyle, count }) {
    const res = await characterApi.generateCharacterImage({
      type: 'character',
      id: characterId,
      appearance_index: 0,
      count,
      art_style: artStyle
    })
    return _extractData(res)
  }

  async function uploadReferenceImage(file) {
    const { cos_key, url } = await directUpload(file, { category: 'upload', biz: 'temp' })
    const res = await characterApi.uploadTempImage({ cos_key })
    return _extractData(res)
  }

  async function updateCharacter(characterId, data) {
    const res = await characterApi.updateCharacter(characterId, data)
    await fetchCharacters()
    return _extractData(res)
  }

  async function deleteCharacter(characterId) {
    await characterApi.deleteCharacter(characterId)
    await fetchCharacters()
  }

  async function createAppearance(data) {
    const res = await appearanceApi.createAppearance(data)
    await fetchCharacters()
    return _extractData(res)
  }

  async function updateAppearance(data) {
    const res = await appearanceApi.updateAppearance(data)
    await fetchCharacters()
    return _extractData(res)
  }

  async function deleteAppearance(appearanceId) {
    await appearanceApi.deleteAppearance(appearanceId)
    await fetchCharacters()
  }

  async function createLocation(data, { silent = false } = {}) {
    const res = await locationApi.createLocation(data)
    if (!silent) {
      await Promise.all([fetchLocations(), fetchProps()])
    }
    return _extractData(res)
  }

  async function updateLocation(locationId, data) {
    const res = await locationApi.updateLocation(locationId, data)
    await Promise.all([fetchLocations(), fetchProps()])
    return _extractData(res)
  }

  async function deleteLocation(locationId) {
    await locationApi.deleteLocation(locationId)
    await Promise.all([fetchLocations(), fetchProps()])
  }

  async function createLocationImage(data) {
    const res = await locationImageApi.createLocationImage(data)
    await Promise.all([fetchLocations(), fetchProps()])
    return _extractData(res)
  }

  async function updateLocationImage(imageId, data) {
    const res = await locationImageApi.updateLocationImage(imageId, data)
    await Promise.all([fetchLocations(), fetchProps()])
    return _extractData(res)
  }

  async function deleteLocationImage(imageId) {
    await locationImageApi.deleteLocationImage(imageId)
    await Promise.all([fetchLocations(), fetchProps()])
  }

  async function createVoice(data) {
    const res = await voiceApi.createVoice(data)
    await fetchVoices()
    return _extractData(res)
  }

  async function updateVoice(voiceId, data) {
    const res = await voiceApi.updateVoice(voiceId, data)
    await fetchVoices()
    return _extractData(res)
  }

  async function deleteVoice(voiceId) {
    await voiceApi.deleteVoice(voiceId)
    await fetchVoices()
  }

  async function bindVoiceToCharacter(characterId, voiceData) {
    const res = await characterApi.updateCharacter(characterId, voiceData)
    await fetchCharacters()
    return _extractData(res)
  }

  function setPage(type, page) {
    sectionPage.value[type] = page
  }

  async function generateLocationImage({ locationId, imageIndex = 0, artStyle = '', count = 3 }) {
    const res = await locationAiApi.generateLocationImage({
      type: 'location',
      id: locationId,
      image_index: imageIndex,
      count,
      art_style: artStyle,
    })
    return _extractData(res)
  }

  async function generatePropImage({ propId, imageIndex = 0, count = 3 }) {
    const res = await locationAiApi.generateLocationImage({
      type: 'prop',
      id: propId,
      image_index: imageIndex,
      count,
    })
    return _extractData(res)
  }

  async function modifyLocationImage({ id, type = 'location', imageIndex = 0, modifyPrompt, extraImageUrls = [] }) {
    const res = await locationAiApi.modifyLocationImage({
      id,
      type,
      image_index: imageIndex,
      modify_prompt: modifyPrompt,
      extra_image_urls: extraImageUrls,
    })
    return _extractData(res)
  }

  async function undoLocationImage({ locationId, imageIndex = 0 }) {
    const res = await locationAiApi.undoLocationImage({
      location_id: locationId,
      image_index: imageIndex,
    })
    await Promise.all([fetchLocations(), fetchProps()])
    return _extractData(res)
  }

  async function undoCharacterImage({ characterId, appearanceIndex }) {
    const res = await characterAiApi.undoCharacterImage({
      id: characterId,
      appearance_index: appearanceIndex,
    })
    await fetchCharacters()
    return _extractData(res)
  }

  async function uploadCharacterImage({ file, characterId, appearanceIndex, imageIndex, labelText, silent = false }) {
    // 直传 COS（原图 + 前端生成的缩略图）
    const { cos_key, thumbnail_cos_key } = await directUploadWithThumbnail(file, { category: 'upload', biz: 'char' })
    // 确认接口更新数据库
    const formData = new FormData()
    formData.append('cos_key', cos_key)
    if (thumbnail_cos_key) {
      formData.append('thumbnail_cos_key', thumbnail_cos_key)
    }
    formData.append('type', 'character')
    formData.append('id', characterId)
    formData.append('appearance_index', String(appearanceIndex))
    formData.append('label_text', labelText || '')
    if (imageIndex != null) {
      formData.append('image_index', String(imageIndex))
    }
    const res = await characterAiApi.uploadCharacterImage(formData)
    if (!silent) await fetchCharacters()
    return _extractData(res)
  }

  async function uploadLocationImage({ file, locationId, imageIndex, labelText, silent = false }) {
    // 直传 COS（原图 + 前端生成的缩略图）
    const { cos_key, thumbnail_cos_key } = await directUploadWithThumbnail(file, { category: 'upload', biz: 'loc' })
    // 确认接口更新数据库
    const formData = new FormData()
    formData.append('cos_key', cos_key)
    if (thumbnail_cos_key) {
      formData.append('thumbnail_cos_key', thumbnail_cos_key)
    }
    formData.append('type', 'location')
    formData.append('id', locationId)
    formData.append('label_text', labelText || '')
    if (imageIndex != null) {
      formData.append('image_index', String(imageIndex))
    }
    const res = await locationAiApi.uploadLocationImage(formData)
    if (!silent) await Promise.all([fetchLocations(), fetchProps()])
    return _extractData(res)
  }

  async function batchDownload() {
    const token = localStorage.getItem('token')
    const params = new URLSearchParams()
    const folderId = resolveFolderIdParam()
    if (folderId) params.set('folder_id', folderId)
    const url = `/api/v1/asset-hub/download?${params.toString()}`
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
    a.download = match?.[1] || `asset-hub_${new Date().toISOString().slice(0, 10)}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(a.href)
  }

  // ==================== 批量同步状态 ====================
  const batchSyncingAssetIds = ref(new Set())
  const batchSyncTotal = ref(0)
  const batchSyncDone = ref(0)
  // 用户已确认、等待后端 asset_hub_batch_sync_started 事件期间为 true
  // 覆盖"点击确认到后端正式回 started"之间的空窗期，避免重复触发
  const batchSyncPending = ref(false)
  const isBatchSyncing = computed(
    () => batchSyncPending.value || batchSyncTotal.value > 0,
  )

  function isAssetBatchSyncing(assetId) {
    return batchSyncingAssetIds.value.has(assetId)
  }
  function setAssetBatchSyncing(assetId, syncing) {
    const next = new Set(batchSyncingAssetIds.value)
    if (syncing) next.add(assetId); else next.delete(assetId)
    batchSyncingAssetIds.value = next
  }
  function markBatchSyncPending() {
    batchSyncPending.value = true
  }
  function markBatchSyncStarted(total, assetIds) {
    batchSyncingAssetIds.value = new Set(assetIds || [])
    // total 用 WS 推来的真实总数，而不是 assetIds.length（避免后端裁剪导致总数不准）
    batchSyncTotal.value = Number(total) || (assetIds || []).length
    batchSyncDone.value = 0
    // 已正式进入同步流程，pending 标记使命完成
    batchSyncPending.value = false
  }
  function incBatchSyncDone() {
    batchSyncDone.value += 1
  }
  function resetBatchSync() {
    batchSyncingAssetIds.value = new Set()
    batchSyncTotal.value = 0
    batchSyncDone.value = 0
    batchSyncPending.value = false
  }

  return {
    UNGROUPED_FOLDER_ID,
    PLATFORM_FOLDER_ID,
    selectedFolderId,
    filter,
    loading,
    folders,
    resolveFolderIdParam,
    characters,
    locations,
    voices,
    props,
    sectionPage,
    pageSize,
    sectionPagination,
    generatingAssetIds: ref(new Map()),
    isAssetGenerating: () => false,
    setAssetGenerating: () => {},
    batchSyncingAssetIds,
    batchSyncTotal,
    batchSyncDone,
    batchSyncPending,
    isBatchSyncing,
    isAssetBatchSyncing,
    setAssetBatchSyncing,
    markBatchSyncPending,
    markBatchSyncStarted,
    incBatchSyncDone,
    resetBatchSync,
    updateAppearanceStatus,
    updateLocationImageStatus,
    updateAppearanceVolcId,
    updateLocationImageVolcId,
    updateVoiceVolcId,
    updateAppearanceImage,
    updateLocationImageState,
    fetchAll,
    selectFolder,
    fetchFolders,
    fetchCharacters,
    fetchLocations,
    fetchProps,
    fetchVoices,
    createFolder,
    updateFolder,
    deleteFolder,
    createCharacter,
    generateCharacterImage,
    uploadReferenceImage,
    updateCharacter,
    deleteCharacter,
    createAppearance,
    updateAppearance,
    deleteAppearance,
    createLocation,
    updateLocation,
    deleteLocation,
    createLocationImage,
    updateLocationImage,
    deleteLocationImage,
    createVoice,
    updateVoice,
    deleteVoice,
    bindVoiceToCharacter,
    setPage,
    generateLocationImage,
    generatePropImage,
    modifyLocationImage,
    undoLocationImage,
    undoCharacterImage,
    uploadCharacterImage,
    uploadLocationImage,
    batchDownload,
  }
})
