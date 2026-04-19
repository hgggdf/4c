import request from './request'

export function sendChatMessage(payload) {
  return request.post('/api/chat', payload)
}
