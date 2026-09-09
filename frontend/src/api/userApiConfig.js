import request from '@/utils/request'

/**
 * 获取当前用户API配置
 */
export function getUserApiConfig() {
  return request.get('/user-api-config')
}

/**
 * 创建用户API配置
 * @param {Object} data - 配置数据
 */
export function createUserApiConfig(data) {
  return request.post('/user-api-config', data)
}

/**
 * 更新当前用户API配置
 * @param {Object} data - 更新数据（支持部分更新）
 */
export function updateUserApiConfig(data) {
  return request.put('/user-api-config', data)
}

/**
 * 测试模型厂商连接
 * @param {string} providerCode - 模型厂商标识
 */
export function testProviderConnection(providerCode) {
  return request.post('/user-api-config/connect', { provider_code: providerCode })
}
