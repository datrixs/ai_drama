import request from '@/utils/request'

/**
 * 获取所有AI供应商列表
 */
export function getAiProviderList() {
  return request.get('/ai-providers')
}
