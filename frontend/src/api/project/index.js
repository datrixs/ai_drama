import request from '@/utils/request'

// 获取项目列表
export function getProjectList(params) {
  return request.get('/projects', { params })
}

// 校验模型配置
export function checkModelConfig() {
  return request.get('/projects/check_analysis_model_config')
}

// 创建项目
// data: { mode?: 'novel'|'director', novel_text?, file_url?, file_name?,
//         title?, video_ratio?, art_style?, expected_episodes? }
// - mode='novel'（默认）：novel_text 必填 ≥20 字，走剧情分析
// - mode='director'：title/video_ratio/art_style/expected_episodes 必填，跳过剧情分析
export function createProject(data) {
  return request.post('/projects', data)
}

// 获取项目详情
export function getProjectDetail(projectId) {
  return request.get(`/projects/${projectId}`)
}

// 编辑项目
export function updateProject(projectId, data) {
  return request.patch(`/projects/${projectId}`, data)
}

// 删除项目
export function deleteProject(projectId) {
  return request.delete(`/projects/${projectId}`)
}

// 确认项目设置
export function confirmProject(projectId, data) {
  return request.put(`/projects/${projectId}/confirm`, data)
}

// 获取项目配置
export function getProjectConfig(projectId) {
  return request.get(`/projects/${projectId}/config`)
}

// 更新项目配置
export function updateProjectConfig(projectId, data) {
  return request.put(`/projects/${projectId}/config`, data)
}

// 获取小说原文
export function getProjectNovelText(projectId) {
  return request.get(`/projects/${projectId}/novel-text`)
}

// 上传小说文件
export function uploadNovel(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/projects/upload/novel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}
