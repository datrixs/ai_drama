import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  createSuperResolutionTask,
  getSuperResolutionTasks,
  cancelSuperResolutionTask,
  retrySuperResolutionTask,
  deleteSuperResolutionTask,
} from '@/api/superResolution'
import { WSEventType, SuperResolutionStatus } from '@/constants/ws'
import { SR_SCENES } from '@/constants/superResolution'

/**
 * 视频超分任务默认参数:以"通用"场景(common)的 defaults 初始化
 *
 * 字段名/类型/value 与火山 API 完全对齐(详见 docs/super_res.md):
 *   - tool_version: 'standard' | 'professional'
 *   - scene: 'common' | 'ugc' | 'short_series' | 'aigc' | 'old_film'
 *   - resolution: '240p'...'4k' | null(不传 = 保持原片)
 *   - bitrate_level: 'low' | 'medium' | 'high'(默认 medium)
 *   - fps: 数字 [15, 120] | null(不传 = 保持原片)
 */
function defaultParams() {
  return {
    tool_version: 'standard',
    scene: 'common',
    resolution: null,
    bitrate_level: 'medium',
    fps: null,
    ...sceneDefaults('common'),
  }
}

/**
 * 取某个场景的 defaults,合并到统一的参数结构
 */
function sceneDefaults(value) {
  const sc = SR_SCENES.find(s => s.value === value) || SR_SCENES[0]
  const d = sc.defaults || {}
  return {
    tool_version: d.tool_version || 'standard',
    resolution: d.resolution ?? null,
    bitrate_level: d.bitrate_level ?? 'medium',
    fps: d.fps ?? null,
  }
}

export const useSuperResolutionStore = defineStore('superResolution', () => {
  // 源视频(直传 COS 后的 URL + 文件元信息)
  const sourceVideoUrl = ref(null)
  const sourceVideoName = ref('')
  const sourceVideoDuration = ref(null)
  const sourceVideoSize = ref(null)
  const sourceThumbnailUrl = ref(null)
  // 是否本地上传: true=COS 资源(后端转永久 URL),false=在线 URL(后端原样存储)
  const sourceIsLocalUpload = ref(true)

  // 任务参数(扁平,与火山 API 字段对齐)
  const params = ref(defaultParams())

  // 任务列表
  const tasks = ref([])
  const currentTaskId = ref(null)
  const isGenerating = ref(false)

  // 分页
  const tasksCursor = ref(null)
  const hasMoreTasks = ref(true)
  const loadingMore = ref(false)

  // 提交中标志:仅用于防止重复点击,与历史任务状态解耦
  // 历史"processing"任务卡住(如 mock 测试收不到回调)不应阻塞新任务提交
  const submitting = ref(false)
  const canGenerate = computed(() => !!sourceVideoUrl.value && !submitting.value)

  // 提交
  async function submit() {
    if (!canGenerate.value || submitting.value) return null
    submitting.value = true

    const payloadParams = buildPayloadParams()
    const optimisticTask = {
      id: 'temp-' + Date.now(),
      source_video_url: sourceVideoUrl.value,
      source_thumbnail_url: sourceThumbnailUrl.value,
      result_video_url: null,
      result_thumbnail_url: null,
      status: SuperResolutionStatus.PENDING,
      progress: 0,
      error_message: null,
      create_time: new Date().toISOString(),
      completed_at: null,
      params: { ...payloadParams },
    }
    tasks.value.unshift(optimisticTask)

    try {
      const data = {
        source_video_url: sourceVideoUrl.value,
        is_local_upload: sourceIsLocalUpload.value,
        ...payloadParams,
      }
      // 仅当缩略图是有效 URL(blob URL 不传后端)时才下发
      if (sourceThumbnailUrl.value && /^https?:\/\//i.test(sourceThumbnailUrl.value)) {
        data.source_thumbnail_url = sourceThumbnailUrl.value
      }
      if (sourceVideoName.value) data.source_video_name = sourceVideoName.value
      if (sourceVideoDuration.value != null) data.source_video_duration = sourceVideoDuration.value

      const res = await createSuperResolutionTask(data)
      currentTaskId.value = res.task_id
      isGenerating.value = true
      const idx = tasks.value.findIndex(t => t.id === optimisticTask.id)
      if (idx >= 0) tasks.value[idx].id = res.task_id
      clearEditor()
      return res
    } catch {
      const idx = tasks.value.findIndex(t => t.id === optimisticTask.id)
      if (idx >= 0) {
        tasks.value[idx].status = SuperResolutionStatus.FAILED
        tasks.value[idx].error_message = '提交失败'
      }
      return null
    } finally {
      submitting.value = false
    }
  }

  /**
   * 把 store.params 翻译成后端载荷(扁平,与火山 API 一致)
   * - null 值不下发(让火山按默认处理)
   * - "与源一致"(resolution=null):不下发 resolution,火山按原片分辨率输出
   */
  function buildPayloadParams() {
    const p = params.value
    const out = {
      tool_version: p.tool_version,
      scene: p.scene,
    }
    if (p.resolution) {
      out.resolution = p.resolution
    }
    if (p.bitrate_level) {
      out.bitrate_level = p.bitrate_level
    }
    if (p.fps) {
      out.fps = Number(p.fps)
    }
    return out
  }

  function handleWsEvent(event) {
    if (event.event_type !== WSEventType.SUPER_RESOLUTION_PROGRESS) return
    const d = event.data
    if (!d?.task_id) return

    const idx = tasks.value.findIndex(t => t.id === d.task_id)
    if (idx >= 0) {
      const task = { ...tasks.value[idx], status: d.status, progress: d.progress ?? tasks.value[idx].progress }
      if (d.result_video_url) task.result_video_url = d.result_video_url
      if (d.result_thumbnail_url) task.result_thumbnail_url = d.result_thumbnail_url
      if (d.error_message) task.error_message = d.error_message
      if (d.status === SuperResolutionStatus.SUCCEEDED || d.status === SuperResolutionStatus.FAILED) {
        task.completed_at = new Date().toISOString()
      }
      tasks.value[idx] = task
    } else {
      tasks.value.unshift({
        id: d.task_id,
        status: d.status,
        progress: d.progress ?? 0,
        source_video_url: d.source_video_url || null,
        source_thumbnail_url: d.source_thumbnail_url || null,
        result_video_url: d.result_video_url || null,
        result_thumbnail_url: d.result_thumbnail_url || null,
        error_message: d.error_message || null,
        params: d.params || null,
        create_time: d.create_time || new Date().toISOString(),
        completed_at: (d.status === SuperResolutionStatus.SUCCEEDED || d.status === SuperResolutionStatus.FAILED) ? new Date().toISOString() : null,
      })
    }

    if ([SuperResolutionStatus.SUCCEEDED, SuperResolutionStatus.FAILED, SuperResolutionStatus.CANCELLED].includes(d.status) && currentTaskId.value === d.task_id) {
      currentTaskId.value = null
      isGenerating.value = false
    }
  }

  async function fetchTasks() {
    try {
      const res = await getSuperResolutionTasks({ limit: 5 })
      tasks.value = res.items || []
      hasMoreTasks.value = res.has_more !== false
      tasksCursor.value = res.next_cursor || null

      const active = tasks.value.find(t =>
        [SuperResolutionStatus.PENDING, SuperResolutionStatus.SUBMITTED, SuperResolutionStatus.PROCESSING].includes(t.status)
      )
      if (active) {
        isGenerating.value = true
        currentTaskId.value = active.id
      }
    } catch (e) {
      console.warn('[superResolution] fetchTasks 失败:', e)
    }
  }

  async function loadMoreTasks() {
    if (loadingMore.value || !hasMoreTasks.value) return
    loadingMore.value = true
    try {
      const res = await getSuperResolutionTasks({ cursor: tasksCursor.value, limit: 5 })
      const newItems = res.items || []
      tasks.value = [...tasks.value, ...newItems]
      hasMoreTasks.value = res.has_more !== false
      tasksCursor.value = res.next_cursor || null
    } catch {
      // 静默
    } finally {
      loadingMore.value = false
    }
  }

  async function cancelTask(taskId) {
    await cancelSuperResolutionTask(taskId)
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx >= 0) tasks.value[idx].status = SuperResolutionStatus.CANCELLED
  }

  async function retryTask(taskId) {
    await retrySuperResolutionTask(taskId)
    const idx = tasks.value.findIndex(t => t.id === taskId)
    if (idx >= 0) {
      tasks.value[idx].status = SuperResolutionStatus.PENDING
      tasks.value[idx].progress = 0
    }
  }

  async function removeTask(taskId) {
    await deleteSuperResolutionTask(taskId)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
  }

  // 编辑器管理
  function setSourceVideo({ url, name, duration, size, thumbnail_url, is_local_upload = true }) {
    sourceVideoUrl.value = url
    sourceVideoName.value = name || ''
    sourceVideoDuration.value = duration ?? null
    sourceVideoSize.value = size ?? null
    sourceThumbnailUrl.value = thumbnail_url || null
    sourceIsLocalUpload.value = !!is_local_upload
  }

  function clearSourceVideo() {
    sourceVideoUrl.value = null
    sourceVideoName.value = ''
    sourceVideoDuration.value = null
    sourceVideoSize.value = null
    sourceThumbnailUrl.value = null
    sourceIsLocalUpload.value = true
  }

  function clearEditor() {
    clearSourceVideo()
    currentTaskId.value = null
  }

  function resetParams() {
    params.value = defaultParams()
  }

  function reset() {
    clearEditor()
    resetParams()
  }

  /**
   * 切换场景预设:仅更新 scene 字段
   * 不再自动套用场景的 tool_version / bitrate_level 默认值
   * (产品决策:用户手动选定的工具版本与码率不应被场景切换覆盖)
   * scene 字段仅影响火山 API 的 scene 参数,其他参数保持用户当前选择
   */
  function applyScene(value) {
    params.value.scene = value
  }

  return {
    // state
    sourceVideoUrl, sourceVideoName, sourceVideoDuration, sourceVideoSize, sourceThumbnailUrl,
    sourceIsLocalUpload,
    params, tasks, currentTaskId, isGenerating,
    tasksCursor, hasMoreTasks, loadingMore,
    // computed
    canGenerate,
    // actions
    submit, fetchTasks, loadMoreTasks, cancelTask, retryTask, removeTask,
    setSourceVideo, clearSourceVideo, clearEditor, resetParams, reset,
    applyScene,
    handleWsEvent,
  }
})

export {
  SR_SCENES,
}
