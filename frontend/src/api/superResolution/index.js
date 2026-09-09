import request from '@/utils/request'

/**
 * 视频超分 API
 * 路径前缀 /super-resolution/，按短视频模块风格命名。后端字段未最终对齐，待校准。
 */

// 提交超分任务
export function createSuperResolutionTask(data) {
  return request.post('/super-resolution/generate', data)
}

// 获取任务列表（游标分页）
export function getSuperResolutionTasks(params = {}) {
  return request.get('/super-resolution/tasks', { params })
}

// 任务详情
export function getSuperResolutionTask(taskId) {
  return request.get(`/super-resolution/tasks/${taskId}`)
}

// 取消任务
export function cancelSuperResolutionTask(taskId) {
  return request.post(`/super-resolution/tasks/${taskId}/cancel`)
}

// 重试任务
export function retrySuperResolutionTask(taskId) {
  return request.post(`/super-resolution/tasks/${taskId}/retry`)
}

// 删除任务
export function deleteSuperResolutionTask(taskId) {
  return request.delete(`/super-resolution/tasks/${taskId}`)
}
