import request from '@/utils/request'

export function getLocationImageList(params) {
  return request.get('/asset-hub/location-images', { params })
}

export function getLocationImageDetail(imageId) {
  return request.get(`/asset-hub/location-images/${imageId}`)
}

export function createLocationImage(data) {
  return request.post('/asset-hub/location-images', data)
}

export function updateLocationImage(imageId, data) {
  return request.put(`/asset-hub/location-images/${imageId}`, data)
}

export function deleteLocationImage(imageId) {
  return request.delete(`/asset-hub/location-images/${imageId}`)
}
