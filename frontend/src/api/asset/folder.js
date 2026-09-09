import request from '@/utils/request'

export function getFolderList(params) {
  return request.get('/asset-hub/folders', { params })
}

export function getFolderDetail(folderId) {
  return request.get(`/asset-hub/folders/${folderId}`)
}

export function createFolder(data) {
  return request.post('/asset-hub/folders', data)
}

export function updateFolder(folderId, data) {
  return request.put(`/asset-hub/folders/${folderId}`, data)
}

export function deleteFolder(folderId) {
  return request.delete(`/asset-hub/folders/${folderId}`)
}
