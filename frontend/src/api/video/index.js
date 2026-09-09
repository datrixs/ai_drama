import request from '@/utils/request'

// 单镜头视频生成
export function generateVideo(projectId, data) {
  return request.post(`/video/projects/${projectId}/generate`, data)
}

// 多片段成片视频生成
export function generateMultimodalVideo(projectId, episodeId, data) {
  return request.post(`/video/projects/${projectId}/episodes/${episodeId}/generate-multimodal`, data)
}

// 按 segment 索引生成单个片段视频
export function generateSegmentVideo(projectId, episodeId, data) {
  return request.post(`/video/projects/${projectId}/episodes/${episodeId}/generate-segment`, data)
}

// 生成多模态脚本
export function generateScript(projectId, episodeId) {
  return request.post(`/video/projects/${projectId}/episodes/${episodeId}/generate-script`, { episode_id: episodeId })
}

// 批量生成脚本（所有未生成的剧集按顺序串行生成）
export function batchGenerateScripts(projectId) {
  return request.post(`/video/projects/${projectId}/episodes/batch-generate-scripts`)
}

// 查询视频任务状态
export function getVideoTaskStatus(projectId, taskId) {
  return request.get(`/video/projects/${projectId}/tasks/${taskId}`)
}

// 获取视频任务列表
export function getVideoTasks(projectId, params) {
  return request.get(`/video/projects/${projectId}/tasks`, { params })
}

// 获取脚本纯文本
export function getScriptText(projectId, episodeId) {
  return request.get(`/video/projects/${projectId}/episodes/${episodeId}/script-text`)
}

// 更新脚本纯文本（segments 为片段对象数组，每项 {segment_index, plain_text}）
export function updateScriptText(projectId, episodeId, segments) {
  return request.put(`/video/projects/${projectId}/episodes/${episodeId}/script-text`, { segments })
}

// 重试任务
export function retryVideoTask(projectId, taskId) {
  return request.post(`/video/projects/${projectId}/tasks/${taskId}/retry`)
}

// 取消任务
export function cancelVideoTask(projectId, taskId) {
  return request.post(`/video/projects/${projectId}/tasks/${taskId}/cancel`)
}

// 拼接剧集视频
export function concatEpisodeVideo(projectId, episodeId) {
  return request.post(`/video/projects/${projectId}/episodes/${episodeId}/concat-video`, { episode_id: episodeId })
}

// 获取剧集整集合成历史
export function getConcatRecords(projectId, episodeId) {
  return request.get(`/video/projects/${projectId}/episodes/${episodeId}/concat-records`)
}
