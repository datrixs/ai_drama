import request from '@/utils/request'

/**
 * 获取积分购买方案列表，需登录
 */
export function getPointPlans() {
  return request.get('/points/plans')
}

/**
 * 查询积分变动记录，需登录
 */
export function getPointRecords(params) {
  return request.get('/points/records', { params })
}
