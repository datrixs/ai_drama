import request from '@/utils/request'

// 获取剧集分镜片段列表
export function getStoryboards(projectId, episodeId) {
  return request.get(`/storyboard/projects/${projectId}/episodes/${episodeId}/storyboards`)
}

// 创建分镜片段
export function createStoryboard(projectId, episodeId, data) {
  return request.post(`/storyboard/projects/${projectId}/episodes/${episodeId}/storyboards`, data)
}

// 更新分镜片段
export function updateStoryboard(projectId, storyboardId, data) {
  return request.put(`/storyboard/projects/${projectId}/storyboards/${storyboardId}`, data)
}

// 删除分镜片段
export function deleteStoryboard(projectId, storyboardId) {
  return request.delete(`/storyboard/projects/${projectId}/storyboards/${storyboardId}`)
}

// 插入分镜片段（在锚点前/后插入空白片段）
export function insertStoryboard(projectId, episodeId, data) {
  return request.post(`/storyboard/projects/${projectId}/episodes/${episodeId}/storyboards/insert`, data)
}

// 更新片段 shots 数据
export function updateStoryboardShots(projectId, storyboardId, shots) {
  return request.put(`/storyboard/projects/${projectId}/storyboards/${storyboardId}/shots`, { shots })
}

// 重排片段顺序
export function reorderStoryboards(projectId, episodeId, segmentIds) {
  return request.put(`/storyboard/projects/${projectId}/episodes/${episodeId}/storyboards/reorder`, { segment_ids: segmentIds })
}

// 触发视频生成
export function generateStoryboardVideo(projectId, storyboardId, data) {
  return request.post(`/storyboard/projects/${projectId}/storyboards/${storyboardId}/generate-video`, data)
}
