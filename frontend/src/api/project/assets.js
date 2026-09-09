import request from '@/utils/request'

// 解析资产（从分析结果创建）
export function parseAssets(projectId) {
  return request.post(`/projects/${projectId}/assets/parse`)
}

// 获取项目资产
export function getAssets(projectId, type = 'all') {
  return request.get(`/projects/${projectId}/assets`, { params: { type } })
}

// 生成单个资产图片
export function generateAssetImage(projectId, assetType, assetId) {
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/generate`)
}

// 批量生成
export function batchGenerate(projectId) {
  return request.post(`/projects/${projectId}/assets/batch_generate`)
}

// 更新资产
export function updateAsset(projectId, assetType, assetId, data) {
  return request.put(`/projects/${projectId}/assets/${assetType}/${assetId}`, data)
}

// 删除资产
export function deleteAsset(projectId, assetType, assetId) {
  return request.delete(`/projects/${projectId}/assets/${assetType}/${assetId}`)
}

// 上传图片（旧模式，文件经过后端）
export function uploadAssetImage(projectId, assetType, assetId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/upload_image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}

// 确认直传图片（新模式，前端直传 COS 后调用）
export function confirmAssetImage(projectId, assetType, assetId, cosKey, thumbnailCosKey = null) {
  const formData = new FormData()
  formData.append('cos_key', cosKey)
  if (thumbnailCosKey) {
    formData.append('thumbnail_cos_key', thumbnailCosKey)
  }
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/upload_image`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000
  })
}

// AI 修图
export function modifyAssetImage(projectId, assetType, assetId, data) {
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/modify_image`, data)
}

// 参考图生图（角色）
export function referenceGenerateCharacter(projectId, assetId, data) {
  return request.post(`/projects/${projectId}/assets/characters/${assetId}/reference_generate`, data)
}

// 提取角色描述（从参考图）
export function extractCharacterDescription(projectId, data) {
  return request.post(`/projects/${projectId}/assets/characters/extract_description`, data)
}

// AI 修改资产描述
export function aiModifyDescription(projectId, assetType, assetId, data) {
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/ai_modify_description`, data)
}

// 从资产中心导入
export function copyFromGlobal(projectId, assetType, assetId, globalAssetId) {
  return request.post(
    `/projects/${projectId}/assets/${assetType}/${assetId}/copy-from-global`,
    { global_asset_id: globalAssetId }
  )
}

// 创建单个资产
export function createAsset(projectId, assetType, data) {
  return request.post(`/projects/${projectId}/assets/${assetType}`, data)
}

// 撤销图片
export function undoImage(projectId, assetType, assetId) {
  return request.post(`/projects/${projectId}/assets/${assetType}/${assetId}/undo_image`)
}

// 上传项目角色语音
export function uploadCharacterVoice(projectId, assetId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post(
    `/projects/${projectId}/assets/characters/${assetId}/upload_voice`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

// 获取全局资产选择器列表（分页）
export function getGlobalAssetPickerList(type, { page = 1, size = 20, asset_kind, folder_id } = {}) {
  return request.get('/asset-hub/picker', {
    params: {
      type, page, size,
      ...(asset_kind ? { asset_kind } : {}),
      ...(folder_id ? { folder_id } : {}),
    }
  })
}

// 获取资产组列表（用于 picker 的资产组筛选）
export function getGlobalAssetFolders({ page = 1, size = 100, name } = {}) {
  return request.get('/asset-hub/folders', {
    params: { page, size, ...(name ? { name } : {}) }
  })
}

// 批量同步项目资产到火山/BytePlus（后端异步任务，按 region 自动选择）
export function batchSyncProjectAssets(projectId) {
  return request.post(`/volc/projects/${projectId}/sync-all-assets`)
}

// 查询项目未同步资产分类计数（用于批量同步弹窗展示）
export function getProjectUnsyncedSummary(projectId) {
  return request.get(`/volc/projects/${projectId}/unsynced-summary`)
}
