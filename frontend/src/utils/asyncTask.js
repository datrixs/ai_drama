import request from '@/utils/request'
import { ElMessage } from 'element-plus'

/**
 * 提交异步任务，优先用 SSE 监听进度，失败降级为轮询
 *
 * @param {string} url - 提交任务的 API 地址
 * @param {object} data - 请求体
 * @param {object} options
 * @param {function} options.onProgress - 进度回调 (progress: number, task: object)
 * @param {number}  options.timeout - 超时(ms)，默认 300000 (5分钟)
 * @param {string}  options.successMsg - 成功提示
 * @param {number}  options.pollInterval - 轮询降级间隔(ms)，默认 2000
 * @returns {Promise<object>} 任务结果
 */
export async function submitAsyncTask(url, data, options = {}) {
  const {
    onProgress,
    timeout = 300000,
    successMsg = '操作成功',
    pollInterval = 2000,
  } = options

  // 1. 提交任务
  const response = await request({ url, method: 'post', data })

  // 同步完成的任务直接返回
  if (!response?.async) {
    ElMessage.success(successMsg)
    return response
  }

  const taskId = response.task_id
  if (!taskId) {
    throw new Error('异步任务未返回 task_id')
  }

  // 2. 优先尝试 SSE
  return new Promise((resolve, reject) => {
    const startTime = Date.now()

    const timer = setTimeout(() => {
      cleanup()
      ElMessage.error('操作超时，请稍后查看结果')
      reject(new Error('任务超时'))
    }, timeout)

    const cleanup = () => {
      clearTimeout(timer)
    }

    const handleTaskUpdate = (task) => {
      if (onProgress) {
        onProgress(task.progress || 0, task)
      }
      if (task.status === 'completed') {
        cleanup()
        ElMessage.success(successMsg)
        resolve(JSON.parse(task.result || '{}'))
      } else if (task.status === 'failed') {
        cleanup()
        const errorMsg = task.error || '操作失败'
        ElMessage.error(errorMsg)
        reject(new Error(errorMsg))
      } else if (task.status === 'canceled') {
        cleanup()
        ElMessage.info('任务已取消')
        reject(new Error('任务已取消'))
      }
    }

    // SSE 模式
    trySSE(taskId, handleTaskUpdate, () => {
      // SSE 连接失败 → 降级轮询
      cleanup()
      fallbackPoll(taskId, handleTaskUpdate, pollInterval, timeout, startTime)
        .then(resolve)
        .catch(reject)
    })
  })
}

function trySSE(taskId, onUpdate, onFallback) {
  const sseUrl = `/api/v1/asset-hub/tasks/${taskId}/stream`
  let fallbackTriggered = false

  const eventSource = new EventSource(sseUrl)

  eventSource.onerror = () => {
    eventSource.close()
    if (!fallbackTriggered) {
      fallbackTriggered = true
      onFallback()
    }
  }

  eventSource.onmessage = (event) => {
    try {
      const task = JSON.parse(event.data)
      if (task.error) {
        eventSource.close()
        if (!fallbackTriggered) {
          fallbackTriggered = true
          onFallback()
        }
        return
      }
      onUpdate(task)
      if (['completed', 'failed', 'canceled'].includes(task.status)) {
        eventSource.close()
      }
    } catch {
      // 解析失败忽略
    }
  }
}

async function fallbackPoll(taskId, onUpdate, interval, timeout, startTime) {
  while (Date.now() - startTime < timeout) {
    await sleep(interval)
    const taskRes = await request({
      url: `/asset-hub/tasks/${taskId}`,
      method: 'get',
    })
    onUpdate(taskRes)
    if (['completed', 'failed', 'canceled'].includes(taskRes.status)) {
      return JSON.parse(taskRes.result || '{}')
    }
  }
  throw new Error('任务超时')
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}
