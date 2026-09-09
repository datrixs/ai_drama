import { reactive, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  generateCanvasImage,
  generateCanvasText,
  generateCanvasVideo,
  getCanvasGeneration,
} from '@/api/canvas'
import { useWebSocket } from '@/composables/useWebSocket'
import { WSEventType } from '@/constants/ws'

/**
 * 画布节点生成提交 + 轮询兜底 + WS 实时通知
 *
 * 优先级：WS 事件即时 apply → 轮询兜底（WS 断连 / 漏推时仍工作）
 *
 * @param {object} opts
 * @param {import('vue').Ref<any[]>} opts.flowNodes
 * @param {(itemId: string, patch: any, vfUpdateNodeData?: Function) => void} opts.updateNodeData
 * @param {() => any} opts.getStoreItem - 从 store.currentDocument.items 取节点
 */
export function useCanvasGeneration({ flowNodes, updateNodeData, getStoreItem }) {
  const generatingItems = reactive(new Set())
  const generationPollTimers = new Map()

  function _cleanupPoll(itemId) {
    const t = generationPollTimers.get(itemId)
    if (t) {
      clearTimeout(t)
      generationPollTimers.delete(itemId)
    }
  }

  function clearAllTimers() {
    generationPollTimers.forEach((t) => clearTimeout(t))
    generationPollTimers.clear()
  }

  async function submit(itemId, itemType, payload) {
    const item = flowNodes.value.find((n) => n.id === itemId)
    if (!item) return null

    generatingItems.add(itemId)
    updateNodeData(itemId, { last_run_status: 'pending', last_run_error: null })

    try {
      let resp
      if (itemType === 'text') {
        resp = await generateCanvasText(itemId, payload)
      } else if (itemType === 'image') {
        resp = await generateCanvasImage(itemId, payload)
      } else if (itemType === 'video') {
        resp = await generateCanvasVideo(itemId, payload)
      } else {
        ElMessage.warning('不支持的节点类型')
        return null
      }

      const generationId = resp?.generation_id
      if (!generationId) throw new Error('未返回 generation_id')
      ElMessage.success('已提交生成任务')
      // 轮询作为 WS 兜底；WS 通常会先到并停掉轮询
      pollGeneration(itemId, generationId, itemType)
      return { generationId, resp }
    } catch (e) {
      generatingItems.delete(itemId)
      updateNodeData(itemId, { last_run_status: 'failed', last_run_error: '提交失败' })
      return null
    }
  }

  function pollGeneration(itemId, generationId, itemType) {
    const intervals = [1500, 2000, 3000, 5000]
    const maxAttempts = 60
    let attempts = 0

    const tick = async () => {
      attempts += 1
      if (attempts > maxAttempts) {
        // 轮询兜底超时：不再继续轮询，但不标记 failed，也不从 generatingItems 移除
        // 状态保持"生成中"（pending/processing），等 WS 回调推送最终结果
        _cleanupPoll(itemId)
        return
      }
      try {
        const gen = await getCanvasGeneration(itemId, generationId)
        if (gen?.status === 'completed') {
          applyGenerationResult(itemId, itemType, gen)
          generatingItems.delete(itemId)
          _cleanupPoll(itemId)
          return
        }
        if (gen?.status === 'failed') {
          updateNodeData(itemId, {
            last_run_status: 'failed',
            last_run_error: gen?.error_msg || '生成失败',
          })
          generatingItems.delete(itemId)
          _cleanupPoll(itemId)
          return
        }
        const delay = intervals[Math.min(attempts, intervals.length) - 1]
        generationPollTimers.set(itemId, setTimeout(tick, delay))
      } catch (e) {
        generationPollTimers.set(itemId, setTimeout(tick, 3000))
      }
    }

    generationPollTimers.set(itemId, setTimeout(tick, intervals[0]))
  }

  function applyGenerationResult(itemId, itemType, gen) {
    const output = gen?.output_json || {}
    const node = flowNodes.value.find((n) => n.id === itemId)
    const prevContent = node?.data?.content_json || {}

    if (itemType === 'text') {
      const text = output.text || ''
      updateNodeData(itemId, {
        last_run_status: 'completed',
        last_run_error: null,
        content_json: { ...prevContent, text },
        last_output_json: { text },
      })
      const docItem = getStoreItem?.(itemId)
      if (docItem) {
        docItem.content_json = { ...(docItem.content_json || {}), text }
        docItem.last_output_json = { text }
        docItem.last_run_status = 'completed'
      }
    } else if (itemType === 'image') {
      const url = output.url || ''
      const thumbnailUrl = output.thumbnail_url || url
      updateNodeData(itemId, {
        last_run_status: 'completed',
        last_run_error: null,
        content_json: { ...prevContent, prompt: prevContent.prompt || '' },
        last_output_json: { url, thumbnail_url: thumbnailUrl },
        cover_url: thumbnailUrl,
      })
      const docItem = getStoreItem?.(itemId)
      if (docItem) {
        docItem.last_output_json = { url, thumbnail_url: thumbnailUrl }
        docItem.cover_url = thumbnailUrl
        docItem.last_run_status = 'completed'
      }
    } else if (itemType === 'video') {
      const url = output.url || ''
      const coverUrl = output.cover_url || ''
      const patch = {
        last_run_status: 'completed',
        last_run_error: null,
        content_json: { ...prevContent, prompt: prevContent.prompt || '' },
        last_output_json: { url },
      }
      if (coverUrl) patch.cover_url = coverUrl
      updateNodeData(itemId, patch)
      const docItem = getStoreItem?.(itemId)
      if (docItem) {
        docItem.last_output_json = { url }
        if (coverUrl) docItem.cover_url = coverUrl
        docItem.last_run_status = 'completed'
      }
    }
  }

  // ── WS 实时通知：完成/失败立即 apply，并停掉该节点的轮询 ──
  function applyFromWsEvent(event) {
    if (event?.event_type !== WSEventType.CANVAS_GENERATION_PROGRESS) return
    const data = event?.data || {}
    const itemId = data.item_id
    if (!itemId || !generatingItems.has(itemId)) return // 未在生成中（可能已 apply 过），忽略

    const patch = data.item_patch || {}
    if (data.status === 'completed') {
      const nodePatch = {
        last_run_status: 'completed',
        last_run_error: null,
        content_json: patch.content_json || {},
        last_output_json: patch.last_output_json || {},
      }
      if (patch.cover_url !== undefined) nodePatch.cover_url = patch.cover_url
      updateNodeData(itemId, nodePatch)
      const docItem = getStoreItem?.(itemId)
      if (docItem) {
        if (patch.content_json) docItem.content_json = patch.content_json
        if (patch.last_output_json) docItem.last_output_json = patch.last_output_json
        if (patch.cover_url !== undefined) docItem.cover_url = patch.cover_url
        docItem.last_run_status = 'completed'
      }
      _cleanupPoll(itemId)
      generatingItems.delete(itemId)
    } else if (data.status === 'failed') {
      const errMsg = data.error_msg || patch.last_run_error || '生成失败'
      updateNodeData(itemId, {
        last_run_status: 'failed',
        last_run_error: errMsg,
      })
      const docItem = getStoreItem?.(itemId)
      if (docItem) {
        docItem.last_run_status = 'failed'
        docItem.last_run_error = errMsg
      }
      _cleanupPoll(itemId)
      generatingItems.delete(itemId)
      ElMessage.error(errMsg)
    }
  }

  const { onEvent } = useWebSocket()
  const unsubscribeWs = onEvent(applyFromWsEvent)

  onBeforeUnmount(() => {
    unsubscribeWs()
    clearAllTimers()
  })

  return {
    generatingItems,
    submit,
    pollGeneration,
    applyGenerationResult,
    clearAllTimers,
  }
}
