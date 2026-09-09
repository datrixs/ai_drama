import request from '@/utils/request'

export function getCharacterList(params) {
  return request.get('/asset-hub/characters', { params })
}

export function getCharacterDetail(characterId) {
  return request.get(`/asset-hub/characters/${characterId}`)
}

export function createCharacter(data) {
  return request.post('/asset-hub/characters', data)
}

export function updateCharacter(characterId, data) {
  return request.put(`/asset-hub/characters/${characterId}`, data)
}

export function deleteCharacter(characterId) {
  return request.delete(`/asset-hub/characters/${characterId}`)
}

export function uploadTempImage(data, options = {}) {
  return request.post('/asset-hub/upload-temp', data, options, { timeout: 180000 })
}

export function generateCharacterImage(data) {
  return request.post('/asset-hub/generate-image', data)
}

export function aiDesignCharacter(data) {
  return request.post('/asset-hub/ai-design-character', data)
}

export function referenceToCharacter(data) {
  return request.post('/asset-hub/reference-to-character', data)
}

export function getTaskStatus(taskId) {
  return request.get(`/asset-hub/tasks/${taskId}`)
}
