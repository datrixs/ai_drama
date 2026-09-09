import request from '@/utils/request'

// 获取剧集列表
export function getEpisodes(projectId) {
  return request.get(`/episodes/projects/${projectId}/episodes`)
}

// 获取单个剧集详情
export function getEpisode(projectId, episodeId) {
  return request.get(`/episodes/projects/${projectId}/episodes/${episodeId}`)
}

// 新增一集空剧集（仅导演模式项目）
export function createEpisode(projectId, data = {}) {
  return request.post(`/episodes/projects/${projectId}/episodes`, data)
}

// 删除剧集（软删，关联分镜一并清理）
export function deleteEpisode(projectId, episodeId) {
  return request.delete(`/episodes/projects/${projectId}/episodes/${episodeId}`)
}

// 更新剧集字段（仅导演模式项目，目前用于改标题）
export function updateEpisode(projectId, episodeId, data) {
  return request.patch(`/episodes/projects/${projectId}/episodes/${episodeId}`, data)
}

// 批量生成分集剧本
export function generateEpisodeScripts(projectId) {
  return request.post(`/episodes/projects/${projectId}/episodes/generate_episode_scripts`)
}

// 重试单集剧本生成
export function retryEpisodeScript(projectId, episodeId) {
  return request.post(`/episodes/projects/${projectId}/episodes/${episodeId}/retry_episode_script`)
}
