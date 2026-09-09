import request from '@/utils/request'

export function getLocationList(params) {
  return request.get('/asset-hub/locations', { params })
}

export function getLocationDetail(locationId) {
  return request.get(`/asset-hub/locations/${locationId}`)
}

export function createLocation(data) {
  return request.post('/asset-hub/locations', data)
}

export function updateLocation(locationId, data) {
  return request.put(`/asset-hub/locations/${locationId}`, data)
}

export function deleteLocation(locationId) {
  return request.delete(`/asset-hub/locations/${locationId}`)
}
