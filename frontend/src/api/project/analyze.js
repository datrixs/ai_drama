import request from '@/utils/request'

// 校验模型配置
export function checkModelConfig() {
  return request.get('/projects/check_analysis_model_config')
}

// 触发/调整分析
export function triggerAnalysis(projectId, data) {
  return request.put(`/projects/${projectId}/analyze`, data)
}

// 获取分析结果
export function getAnalysis(projectId) {
  return request.get(`/projects/${projectId}/analysis`)
}

// AI 故事扩写
export function aiExpandStory(prompt) {
  return request.post('/projects/ai_story_expand', { prompt })
}
