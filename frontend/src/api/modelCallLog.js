import request from '@/utils/request'
import axios from 'axios'

const baseURL = '/api/v1'

/**
 * 获取扣费记录列表（含分页信息）
 * @param {Object} params - 查询参数
 */
export async function getModelCallLogs(params) {
  const token = localStorage.getItem('token')
  const res = await axios.get(`${baseURL}/model-call-logs`, {
    params,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const body = res.data
  if (body.code === 0) {
    return {
      data: body.data || [],
      pagination: body.pagination || null,
    }
  }
  const { ElMessage } = await import('element-plus')
  ElMessage.error(body.msg || '请求失败')
  return Promise.reject(new Error(body.msg || '请求失败'))
}

/**
 * 获取扣费记录统计摘要
 * @param {Object} params - 查询参数
 */
export function getModelCallLogSummary(params) {
  return request.get('/model-call-logs/summary', { params })
}

/**
 * 获取扣费记录详情
 * @param {string} recordId - 记录ID
 */
export function getModelCallLogDetail(recordId) {
  return request.get(`/model-call-logs/${recordId}`)
}
