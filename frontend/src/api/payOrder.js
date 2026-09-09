import request from '@/utils/request'

/**
 * 创建会员购买订单，需登录
 * @param {{ level_id: string, subscribe_type: 'monthly'|'yearly', pay_channel: string }} data
 */
export function createMembershipOrder(data) {
  return request.post('/pay-orders/membership', data)
}

/**
 * 创建积分购买订单，需登录
 * @param {{ plan_id: string, pay_channel: string }} data
 */
export function createPointOrder(data) {
  return request.post('/pay-orders/points', data)
}

/**
 * 查询订单列表，需登录
 * @param {{ page?: number, size?: number, order_type?: number, status?: number }} params
 */
export function getPayOrders(params) {
  return request.get('/pay-orders', { params })
}

/**
 * 查询订单详情，需登录
 * @param {string} orderNo
 */
export function getPayOrderDetail(orderNo) {
  return request.get(`/pay-orders/${orderNo}`)
}

/**
 * 查询充值与积分流水合并记录，需登录
 * @param {{ page?: number, size?: number, type?: string }} params
 *   type: membership/point_purchase/monthly_grant/daily_grant/expire_clear
 */
export function getCombinedRecords(params) {
  return request.get('/pay-orders/combined-records', { params })
}
