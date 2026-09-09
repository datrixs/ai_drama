import request from '@/utils/request'

// ===== 画布 =====

export function listCanvasDocuments() {
  return request.get('/canvas/documents')
}

export function createCanvasDocument(data) {
  return request.post('/canvas/documents', data)
}

export function getCanvasDocument(documentId) {
  return request.get(`/canvas/documents/${documentId}`)
}

export function updateCanvasDocument(documentId, data) {
  return request.put(`/canvas/documents/${documentId}`, data)
}

export function deleteCanvasDocument(documentId) {
  return request.delete(`/canvas/documents/${documentId}`)
}

// ===== 节点 =====

export function createCanvasItem(documentId, data) {
  return request.post(`/canvas/documents/${documentId}/items`, data)
}

export function updateCanvasItem(itemId, data) {
  return request.put(`/canvas/items/${itemId}`, data)
}

export function deleteCanvasItem(itemId) {
  return request.delete(`/canvas/items/${itemId}`)
}

export function batchUpdateCanvasItems(documentId, updates) {
  return request.post(`/canvas/documents/${documentId}/items/batch`, { updates })
}

// ===== 连线 =====

export function createCanvasConnection(documentId, data) {
  return request.post(`/canvas/documents/${documentId}/connections`, data)
}

export function deleteCanvasConnection(connectionId) {
  return request.delete(`/canvas/connections/${connectionId}`)
}

// ===== 节点生成（阶段 3）=====

export function generateCanvasText(itemId, payload = {}) {
  return request.post(`/canvas/items/${itemId}/generate-text`, payload)
}

export function generateCanvasImage(itemId, payload = {}) {
  return request.post(`/canvas/items/${itemId}/generate-image`, payload)
}

export function generateCanvasVideo(itemId, payload = {}) {
  return request.post(`/canvas/items/${itemId}/generate-video`, payload)
}

export function getCanvasGeneration(itemId, generationId) {
  return request.get(`/canvas/items/${itemId}/generations/${generationId}`)
}

export function listCanvasGenerations(itemId, params = {}) {
  return request.get(`/canvas/items/${itemId}/generations`, { params })
}

export function applyCanvasGeneration(itemId, generationId) {
  return request.post(`/canvas/items/${itemId}/generations/${generationId}/apply`)
}

export function getCanvasGenerationModelCall(itemId, generationId) {
  return request.get(`/canvas/items/${itemId}/generations/${generationId}/model-call`)
}

// ===== 资产导入（上传 / 资产中心）=====

export function registerCanvasAsset(itemId, payload = {}) {
  return request.post(`/canvas/items/${itemId}/register-asset`, payload)
}

export function uploadCanvasAsset(itemId, file) {
  const form = new FormData()
  form.append('file', file)
  return request.post(`/canvas/items/${itemId}/upload-asset`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ===== 同步火山 / 保存到资产中心 =====

export function syncCanvasItemVolcano(itemId) {
  return request.post(`/canvas/items/${itemId}/sync-volcano`)
}

export function saveCanvasItemToAssetCenter(itemId, payload = {}) {
  return request.post(`/canvas/items/${itemId}/save-to-asset-center`, payload)
}

export function batchSaveCanvasItemsToAssetCenter(documentId, payload = {}) {
  return request.post(`/canvas/documents/${documentId}/batch-save-to-asset-center`, payload)
}
