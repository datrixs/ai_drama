import request from '@/utils/request'

export function getDramaList(params) {
  return request.get('/dramas', { params })
}

export function getDramaDetail(id) {
  return request.get(`/dramas/${id}`)
}
