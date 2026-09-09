import request from '@/utils/request'

/**
 * 发起转账
 */
export function createTransfer(data) {
  return request.post('/transfers', data)
}

/**
 * 获取转账记录列表
 */
export function getTransferRecords(params) {
  return request.get('/transfers/records', { params })
}
