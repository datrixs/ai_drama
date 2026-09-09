const MOCK_MODE = false

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  generateShortVideo,
  getShortVideoTasks,
  cancelShortVideoTask,
  retryShortVideoTask,
  deleteShortVideoTask,
  getProjectAssetsForPicker,
  getAssetCenterForPicker,
} from '@/api/shortVideo'
import { WSEventType, ShortVideoStatus } from '@/constants/ws'

// 输入限制
export const INPUT_LIMITS = {
  maxImages: 9,
  maxVideos: 3,
  maxAudios: 3,
  maxTotal: 12,
}

export const useShortVideoStore = defineStore('shortVideo', () => {
  // 生成参数
  const generationType = ref('reference') // reference | first_last_frame
  const promptText = ref('')
  const ratio = ref('16:9')
  const resolution = ref('720p')
  const duration = ref(5)
  const generateAudio = ref(true)

  // 首尾帧
  const firstFrameUrl = ref(null)
  const lastFrameUrl = ref(null)
  const firstFrameVolcId = ref(null)
  const lastFrameVolcId = ref(null)

  // 参考媒体 [{url, name, refLabel}] — refLabel 如 "图片1"、"视频2"
  const referenceImages = ref([])
  const referenceVideos = ref([])
  const referenceAudios = ref([])

  // 任务相关
  const tasks = ref([])
  const currentTaskId = ref(null)
  const isGenerating = ref(false)

  // 分页状态
  const tasksCursor = ref(null)
  const hasMoreTasks = ref(true)
  const loadingMore = ref(false)

  // 资产选择器
  const projectAssets = ref([])
  const assetCenterAssets = ref([])
  const loadingAssets = ref(false)

  // 计算属性
  const totalRefCount = computed(() =>
    referenceImages.value.length + referenceVideos.value.length + referenceAudios.value.length
  )

  const canGenerate = computed(() => {
    if (!promptText.value.trim()) return false
    if (generationType.value === 'first_last_frame') {
      if (!firstFrameUrl.value || !lastFrameUrl.value) return false
    }
    return true
  })

  const referenceMediaJson = computed(() => {
    const payload = {}
    const images = referenceImages.value.filter(r => r.url).map(r => ({
      url: r.url,
      thumbnail_url: r.thumbnail_url || null,
      volc_asset_id: r.volc_asset_id || null,
    }))
    const videos = referenceVideos.value.filter(r => r.url).map(r => ({
      url: r.url,
      thumbnail_url: r.thumbnail_url || null,
      volc_asset_id: r.volc_asset_id || null,
      duration: r.duration || null,
    }))
    const audios = referenceAudios.value.filter(r => r.url).map(r => ({ url: r.url, volc_asset_id: r.volc_asset_id || null, duration: r.duration || null }))
    if (images.length) payload.images = images
    if (videos.length) payload.videos = videos
    if (audios.length) payload.audios = audios
    return Object.keys(payload).length > 0 ? JSON.stringify(payload) : null
  })

  // 方法
  async function submit() {
    if (!canGenerate.value) return

    // 乐观更新：立即在 tasks 头部插入临时记录
    const optimisticTask = {
      id: 'temp-' + Date.now(),
      generation_type: generationType.value,
      prompt_text: promptText.value,
      ratio: ratio.value,
      resolution: resolution.value,
      duration: duration.value,
      generate_audio: generateAudio.value,
      status: ShortVideoStatus.PENDING,
      progress: 0,
      video_url: null,
      thumbnail_url: null,
      first_frame_url: firstFrameUrl.value,
      last_frame_url: lastFrameUrl.value,
      reference_media_json: referenceMediaJson.value,
      error_message: null,
      create_time: new Date().toISOString(),
      submitted_at: null,
      completed_at: null,
    }
    tasks.value.unshift(optimisticTask)

    // ── Mock 模式：模拟进度和完成，不调用后端 ──
    if (MOCK_MODE) {
      const tempId = optimisticTask.id
      clearEditor()
      let progress = 0
      const mockVideoUrl = 'https://www.w3schools.com/html/mov_bbb.mp4'
      const mockThumbUrl = ''
      const timer = setInterval(() => {
        progress += Math.floor(Math.random() * 20) + 10
        if (progress >= 100) {
          progress = 100
          clearInterval(timer)
          const t = tasks.value.find(t => t.id === tempId)
          if (t) {
            t.status = 'completed'
            t.progress = 100
            t.video_url = mockVideoUrl
            t.thumbnail_url = mockThumbUrl
            t.completed_at = new Date().toISOString()
          }
        } else {
          const t = tasks.value.find(t => t.id === tempId)
          if (t) {
            t.status = 'processing'
            t.progress = progress
          }
        }
      }, 800)
      return { task_id: tempId }
    }

    try {
      const data = {
        generation_type: generationType.value,
        prompt_text: promptText.value,
        ratio: ratio.value,
        resolution: resolution.value,
        duration: duration.value,
        generate_audio: generateAudio.value,
        reference_media_json: referenceMediaJson.value,
      }
      if (generationType.value === 'first_last_frame') {
        data.first_frame_url = firstFrameUrl.value
        data.last_frame_url = lastFrameUrl.value
        if (firstFrameVolcId.value) data.first_frame_volc_id = firstFrameVolcId.value
        if (lastFrameVolcId.value) data.last_frame_volc_id = lastFrameVolcId.value
      }
      const res = await generateShortVideo(data)
      currentTaskId.value = res.task_id
      // 替换临时 ID 为真实 ID
      const idx = tasks.value.findIndex(t => t.id === optimisticTask.id)
      if (idx >= 0) tasks.value[idx].id = res.task_id
      // 提交成功后清空编辑器
      clearEditor()
      return res
    } catch {
      // 标记临时记录为失败
      const idx = tasks.value.findIndex(t => t.id === optimisticTask.id)
      if (idx >= 0) {
        tasks.value[idx].status = ShortVideoStatus.FAILED
        tasks.value[idx].error_message = '提交失败'
      }
      return null
    }
  }

  /** 处理 WebSocket 推送的短视频进度事件 */
  function handleWsEvent(event) {
    if (event.event_type !== WSEventType.SHORT_VIDEO_PROGRESS) return
    const d = event.data
    if (!d?.task_id) return

    const idx = tasks.value.findIndex(t => t.id === d.task_id)
    if (idx >= 0) {
      const task = { ...tasks.value[idx], status: d.status, progress: d.progress ?? tasks.value[idx].progress }
      if (d.video_url) task.video_url = d.video_url
      if (d.thumbnail_url) task.thumbnail_url = d.thumbnail_url
      if (d.error_message) task.error_message = d.error_message
      if (d.api_task_id) task.api_task_id = d.api_task_id
      if (d.status === ShortVideoStatus.SUCCEEDED || d.status === ShortVideoStatus.FAILED) {
        task.completed_at = new Date().toISOString()
      }
      tasks.value[idx] = task
    } else {
      // WS 事件先于乐观更新到达，直接插入
      tasks.value.unshift({
        id: d.task_id,
        status: d.status,
        progress: d.progress ?? 0,
        video_url: d.video_url || null,
        thumbnail_url: d.thumbnail_url || null,
        error_message: d.error_message || null,
        api_task_id: d.api_task_id || null,
        completed_at: (d.status === ShortVideoStatus.SUCCEEDED || d.status === ShortVideoStatus.FAILED) ? new Date().toISOString() : null,
      })
    }

    // 终态清除当前任务标记
    if ([ShortVideoStatus.SUCCEEDED, ShortVideoStatus.FAILED, ShortVideoStatus.CANCELLED].includes(d.status) && currentTaskId.value === d.task_id) {
      currentTaskId.value = null
      isGenerating.value = false
    }
  }

  async function fetchTasks() {
    try {
      const res = await getShortVideoTasks({ limit: 5 })
      tasks.value = res.items || []
      hasMoreTasks.value = res.has_more !== false
      tasksCursor.value = res.next_cursor || null

      // 标记进行中的任务
      const active = tasks.value.find(t =>
        [ShortVideoStatus.PENDING, ShortVideoStatus.SUBMITTED, ShortVideoStatus.QUEUED, ShortVideoStatus.PROCESSING].includes(t.status)
      )
      if (active) {
        isGenerating.value = true
        currentTaskId.value = active.id
      }
    } catch (e) {
      console.warn('[shortVideo] fetchTasks 失败:', e)
    }
  }

  async function loadMoreTasks() {
    if (loadingMore.value || !hasMoreTasks.value) return
    loadingMore.value = true
    try {
      const res = await getShortVideoTasks({
        cursor: tasksCursor.value,
        limit: 5,
      })
      // 新数据追加到尾部（时间更早的记录）
      const newItems = res.items || []
      tasks.value = [...tasks.value, ...newItems]
      hasMoreTasks.value = res.has_more !== false
      tasksCursor.value = res.next_cursor || null
    } catch {
      // 静默处理
    } finally {
      loadingMore.value = false
    }
  }

  async function cancelTask(taskId) {
    await cancelShortVideoTask(taskId)
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx >= 0) tasks.value[idx].status = ShortVideoStatus.CANCELLED
  }

  async function retryTask(taskId) {
    await retryShortVideoTask(taskId)
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx >= 0) {
      tasks.value[idx].status = ShortVideoStatus.PENDING
      tasks.value[idx].progress = 0
    }
  }

  async function removeTask(taskId) {
    await deleteShortVideoTask(taskId)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
  }

  // 资产选择器
  async function fetchProjectAssets() {
    loadingAssets.value = true
    try {
      projectAssets.value = await getProjectAssetsForPicker()
    } catch {
      // 静默处理
    } finally {
      loadingAssets.value = false
    }
  }

  async function fetchAssetCenter() {
    loadingAssets.value = true
    try {
      assetCenterAssets.value = await getAssetCenterForPicker()
    } catch {
      // 静默处理
    } finally {
      loadingAssets.value = false
    }
  }

  // 引用管理
  function getRefCount(type) {
    const map = { image: referenceImages, video: referenceVideos, audio: referenceAudios }
    return map[type]?.value.length || 0
  }

  function _nextRefLabel(type) {
    const count = getRefCount(type)
    const prefix = type === 'image' ? '图片' : type === 'video' ? '视频' : '音频'
    return `${prefix}${count + 1}`
  }

  function addReference(type, item) {
    const listMap = { image: referenceImages, video: referenceVideos, audio: referenceAudios }
    const limitMap = { image: INPUT_LIMITS.maxImages, video: INPUT_LIMITS.maxVideos, audio: INPUT_LIMITS.maxAudios }
    const list = listMap[type]
    const limit = limitMap[type]

    if (totalRefCount.value >= INPUT_LIMITS.maxTotal) return false
    if (list.value.length >= limit) return false
    if (list.value.some(r => r.url === item.url)) return false

    // 自动生成 refLabel
    if (!item.refLabel) {
      item.refLabel = _nextRefLabel(type)
    }

    list.value.push(item)
    return true
  }

  function removeReference(type, index) {
    const listMap = { image: referenceImages, video: referenceVideos, audio: referenceAudios }
    listMap[type].value.splice(index, 1)
    // 重新编号
    _relabel(type)
  }

  function _relabel(type) {
    const listMap = { image: referenceImages, video: referenceVideos, audio: referenceAudios }
    const prefix = type === 'image' ? '图片' : type === 'video' ? '视频' : '音频'
    const list = listMap[type]
    list.value.forEach((item, i) => {
      item.refLabel = `${prefix}${i + 1}`
    })
  }

  function removeReferenceByLabel(refLabel) {
    const listMap = { image: referenceImages, video: referenceVideos, audio: referenceAudios }
    for (const [type, list] of Object.entries(listMap)) {
      const idx = list.value.findIndex(r => r.refLabel === refLabel)
      if (idx >= 0) {
        list.value.splice(idx, 1)
        _relabel(type)
        return true
      }
    }
    return false
  }

  function clearReferences() {
    referenceImages.value = []
    referenceVideos.value = []
    referenceAudios.value = []
  }

  function clearEditor() {
    promptText.value = ''
    firstFrameUrl.value = null
    lastFrameUrl.value = null
    firstFrameVolcId.value = null
    lastFrameVolcId.value = null
    clearReferences()
    currentTaskId.value = null
  }

  function restoreFromTask(task) {
    generationType.value = task.generation_type || 'reference'
    ratio.value = task.ratio || '16:9'
    resolution.value = task.resolution || '720p'
    duration.value = task.duration || 5
    generateAudio.value = task.generate_audio ?? true

    firstFrameUrl.value = task.first_frame_url || null
    lastFrameUrl.value = task.last_frame_url || null
    firstFrameVolcId.value = task.first_frame_volc_id || null
    lastFrameVolcId.value = task.last_frame_volc_id || null

    clearReferences()

    // 先还原参考素材，再设置 promptText —— 编辑器渲染 @图片N 需要 references 已就位
    const refJson = task.reference_media_json
    if (refJson) {
      try {
        const data = typeof refJson === 'string' ? JSON.parse(refJson) : refJson
        // 新格式 images: [{url, thumbnail_url, volc_asset_id}]
        if (data.images) {
          data.images.forEach((item, i) => {
            const url = typeof item === 'string' ? item : item?.url || ''
            const thumbUrl = typeof item === 'object' ? item?.thumbnail_url || null : null
            const volcId = typeof item === 'object' ? item?.volc_asset_id || null : null
            if (url) addReference('image', { url, name: '', refLabel: `图片${i + 1}`, thumbnail_url: thumbUrl, volc_asset_id: volcId })
          })
        }
        // 旧格式 imageUrls: [url]
        if (data.imageUrls) {
          data.imageUrls.forEach((url, i) => {
            if (url) addReference('image', { url, name: '', refLabel: `图片${i + 1}`, volc_asset_id: null })
          })
        }
        // 新格式 videos / audios
        if (data.videos) {
          data.videos.forEach((item, i) => {
            const url = typeof item === 'string' ? item : item?.url || ''
            const thumbUrl = typeof item === 'object' ? item?.thumbnail_url || null : null
            const volcId = typeof item === 'object' ? item?.volc_asset_id || null : null
            const duration = typeof item === 'object' ? item?.duration || null : null
            if (url) addReference('video', { url, name: '', refLabel: `视频${i + 1}`, thumbnail_url: thumbUrl, volc_asset_id: volcId, duration })
          })
        }
        // 旧格式兼容
        if (data.videoUrls) {
          data.videoUrls.forEach((url, i) => {
            if (url) addReference('video', { url, name: '', refLabel: `视频${i + 1}`, volc_asset_id: null })
          })
        }
        if (data.audios) {
          data.audios.forEach((item, i) => {
            const url = typeof item === 'string' ? item : item?.url || ''
            const volcId = typeof item === 'object' ? item?.volc_asset_id || null : null
            const duration = typeof item === 'object' ? item?.duration || null : null
            if (url) addReference('audio', { url, name: '', refLabel: `音频${i + 1}`, volc_asset_id: volcId, duration })
          })
        }
        if (data.audioUrls) {
          data.audioUrls.forEach((url, i) => {
            if (url) addReference('audio', { url, name: '', refLabel: `音频${i + 1}`, volc_asset_id: null })
          })
        }
      } catch { /* ignore */ }
    }

    promptText.value = task.prompt_text || ''
  }

  function reset() {
    generationType.value = 'reference'
    promptText.value = ''
    ratio.value = '16:9'
    resolution.value = '720p'
    duration.value = 5
    generateAudio.value = true
    firstFrameUrl.value = null
    lastFrameUrl.value = null
    firstFrameVolcId.value = null
    lastFrameVolcId.value = null
    clearReferences()
    currentTaskId.value = null
  }

  return {
    // 状态
    generationType, promptText, ratio, resolution, duration, generateAudio,
    firstFrameUrl, lastFrameUrl, firstFrameVolcId, lastFrameVolcId,
    referenceImages, referenceVideos, referenceAudios,
    tasks, currentTaskId, isGenerating,
    tasksCursor, hasMoreTasks, loadingMore,
    projectAssets, assetCenterAssets, loadingAssets,
    // 计算属性
    canGenerate, referenceMediaJson, totalRefCount,
    // 方法
    submit, fetchTasks, loadMoreTasks, cancelTask, retryTask, removeTask,
    fetchProjectAssets, fetchAssetCenter,
    addReference, removeReference, removeReferenceByLabel, clearReferences,
    getRefCount, handleWsEvent,
    clearEditor, restoreFromTask, reset,
  }
})
