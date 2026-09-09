import request from '@/utils/request'

/**
 * 获取所有会员等级（含权益和价格），无需登录
 */
export function getMembershipLevels() {
  return request.get('/membership/levels')
}

/**
 * 获取当前用户会员信息，需登录
 * 返回含 next_level（降级预购）、auto_renew、granted_balance、purchased_balance
 */
export function getCurrentMembership() {
  return request.get('/membership/current')
}

/**
 * 预览会员变更（升降级）
 * @param {{ target_level_id: string, subscribe_type?: string }} data
 * @returns {{ change_type, pay_amount, point_adjust, effective_time, expire_time, message }}
 */
export function getChangePreview(data) {
  return request.post('/membership/change-preview', data)
}
