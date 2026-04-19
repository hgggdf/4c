import request from './request'

// POST /api/chat
// payload: { message, targets, history }
export function sendChatMessage(payload) {
  return request.post('/api/chat', payload)
}
