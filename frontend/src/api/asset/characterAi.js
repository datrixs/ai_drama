import request from '@/utils/request'

export function aiDesignCharacter(data) {
  return request.post('/asset-hub/ai-design-character', data)
}

export function generateImage(data) {
  return request.post('/asset-hub/generate-image', data)
}

export function selectImage(data) {
  return request.post('/asset-hub/select-image', data)
}

export function aiModifyCharacter(data) {
  return request.post('/asset-hub/ai-modify-character', data)
}

export function undoCharacterImage(data) {
  return request.post('/asset-hub/undo-image', data)
}

export function uploadCharacterImage(formData) {
  return request.post('/asset-hub/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}
