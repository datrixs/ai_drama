import request from '@/utils/request'

/**
 * 获取当前登录用户信息
 */
export function getUserInfo() {
  return request.get('/user/me')
}

/**
 * 切换当前主账号的区域类型（domestic/overseas）
 */
export function updateUserRegion(region) {
  return request.put('/user/region', { region })
}

/**
 * 修改当前登录用户密码（需校验原密码）
 * @param {{ old_password: string, new_password: string }} data
 */
export function changePassword(data) {
  return request.put('/user/password', data)
}
