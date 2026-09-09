import request from '@/utils/request'

export function getSubUsers() {
  return request.get('/sub-users')
}

export function getMainUserFolders() {
  return request.get('/sub-users/folders')
}

export function createSubUser(data) {
  return request.post('/sub-users', data)
}

export function updateSubUser(userId, data) {
  return request.put(`/sub-users/${userId}`, data)
}

export function deleteSubUser(userId) {
  return request.delete(`/sub-users/${userId}`)
}

export function transferBalance(userId, amount) {
  return request.post(`/sub-users/${userId}/transfer-balance`, { amount })
}

export function reclaimBalance(userId) {
  return request.post(`/sub-users/${userId}/reclaim-balance`)
}
