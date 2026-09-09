import request from '@/utils/request'

export function aiDesignLocation(data) {
  return request.post('/asset-hub/ai-design-location', data)
}

export function aiModifyLocation(data) {
  return request.post('/asset-hub/ai-modify-location', data)
}

export function aiModifyProp(data) {
  return request.post('/asset-hub/ai-modify-prop', data)
}

export function generateLocationImage(data) {
  return request.post('/asset-hub/generate-image', data)
}

export function modifyLocationImage(data) {
  return request.post('/asset-hub/modify-image', data)
}

export function undoLocationImage(data) {
  return request.post('/asset-hub/undo-location-image', data)
}

export function uploadLocationImage(formData) {
  return request.post('/asset-hub/upload-image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 180000
  })
}
