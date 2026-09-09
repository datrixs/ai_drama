import request from '@/utils/request'

// 创建对话
export function createConversation(projectId, data) {
  return request.post(`/conversation/projects/${projectId}/conversations`, data)
}

// 获取对话列表
export function getConversations(projectId) {
  return request.get(`/conversation/projects/${projectId}/conversations`)
}

// 发送消息
export function sendMessage(projectId, conversationId, data) {
  return request.post(`/conversation/projects/${projectId}/conversations/${conversationId}/messages`, data)
}

// 获取对话详情
export function getConversationDetail(projectId, conversationId) {
  return request.get(`/conversation/projects/${projectId}/conversations/${conversationId}`)
}
