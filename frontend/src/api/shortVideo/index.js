import request from '@/utils/request'

// 提交短视频生成任务
export function generateShortVideo(data) {
  return request.post('/short-video/generate', data)
}

// 获取任务列表（支持游标分页）
export function getShortVideoTasks(params = {}) {
  return request.get('/short-video/tasks', { params })
}

// 获取任务详情
export function getShortVideoTask(taskId) {
  return request.get(`/short-video/tasks/${taskId}`)
}

// 取消任务
export function cancelShortVideoTask(taskId) {
  return request.post(`/short-video/tasks/${taskId}/cancel`)
}

// 重试任务
export function retryShortVideoTask(taskId) {
  return request.post(`/short-video/tasks/${taskId}/retry`)
}

// 删除任务
export function deleteShortVideoTask(taskId) {
  return request.delete(`/short-video/tasks/${taskId}`)
}

// 上传/记录资产
export function uploadShortVideoAsset(data) {
  return request.post('/short-video/assets/upload', data)
}

// 获取资产列表
export function getShortVideoAssets(params) {
  return request.get('/short-video/assets', { params })
}

// 删除资产
export function deleteShortVideoAsset(assetId) {
  return request.delete(`/short-video/assets/${assetId}`)
}

// 获取项目资产库列表（按项目分组）
export function getProjectAssetsForPicker() {
  return request.get('/short-video/project-assets')
}

// 获取资产中心列表
export function getAssetCenterForPicker() {
  return request.get('/short-video/asset-center')
}

// 获取资产中心文件夹列表
export function getAssetCenterFolders() {
  return request.get('/short-video/asset-center/folders')
}

// 同步用户级资产到火山私域
export function syncUserAssetToVolc(assetId, assetKind) {
  return request.post('/volc/user/sync-asset', {
    asset_id: assetId,
    asset_kind: assetKind,
  })
}

// 查询当前用户未同步资产分类计数（用于批量同步弹窗）
// folderId 三态：undefined/null=全部，'null'=未分组，其他=指定资产组
export function getUserUnsyncedSummary(folderId) {
  const params = folderId ? { folder_id: folderId } : {}
  return request.get('/volc/user/unsynced-summary', { params })
}

// 触发用户资产批量同步任务（异步）
export function syncAllUserAssets(folderId) {
  const data = folderId ? { folder_id: folderId } : {}
  return request.post('/volc/user/sync-all-assets', data)
}
