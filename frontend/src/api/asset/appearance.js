import request from '@/utils/request'

export function getAppearanceList(params) {
  return request.get('/asset-hub/character-appearances', { params })
}

export function getAppearanceDetail(appearanceId) {
  return request.get(`/asset-hub/character-appearances/${appearanceId}`)
}

export function createAppearance(data) {
  return request.post('/asset-hub/character-appearances', data)
}

export function updateAppearance(data) {
  return request.patch('/asset-hub/appearances', data)
}

export function deleteAppearance(appearanceId) {
  return request.delete(`/asset-hub/character-appearances/${appearanceId}`)
}
