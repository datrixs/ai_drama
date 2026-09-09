import request from '@/utils/request'
import { submitAsyncTask } from '@/utils/asyncTask'

export function getVoiceList(params) {
  return request.get('/asset-hub/voices', { params })
}

export function getVoiceDetail(voiceId) {
  return request.get(`/asset-hub/voices/${voiceId}`)
}

export function createVoice(data) {
  return request.post('/asset-hub/voices', data)
}

export function updateVoice(voiceId, data) {
  return request.put(`/asset-hub/voices/${voiceId}`, data)
}

export function deleteVoice(voiceId) {
  return request.delete(`/asset-hub/voices/${voiceId}`)
}

export function uploadVoice(formData) {
  return request.post('/asset-hub/voices/upload', formData)
}

/**
 * AI 设计音色（异步任务模式）
 * 后端提交 Celery 任务，通过 SSE/轮询获取结果
 */
export function designVoice(data, options = {}) {
  return submitAsyncTask('/asset-hub/voices/design', data, {
    successMsg: '音色生成完成',
    timeout: 180000,
    ...options,
  })
}
