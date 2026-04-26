import request from './request'

// POST /api/chat
// payload: { message, targets, history }
export function sendChatMessage(payload) {
  return request.post('/api/chat', payload)
}

<<<<<<< Updated upstream
// POST /api/upload_pdf
// 上传 PDF 到知识库
=======
// POST /api/chat/stream
export function sendChatMessageStream(payload, onChunk) {
  return fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(async (response) => {
    if (!response.ok) {
      let errText = ''
      try {
        errText = await response.text()
      } catch { /* ignore */ }
      if (errText.includes('<!DOCTYPE') || errText.includes('<html')) {
        errText = `服务器返回 ${response.status} 错误，请确认后端已启动`
      }
      throw new Error(errText || `服务器错误 (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        for (const line of part.split('\n')) {
          if (!line.startsWith('data: ')) continue
          const data = line.slice(6)
          if (data === '[DONE]') continue
          try {
            const parsed = JSON.parse(data)
            // 后端格式：{type, content} / {type, tool, args} 等
            if (parsed.type !== 'done') {
              onChunk(parsed)
            }
          } catch { /* ignore malformed JSON */ }
        }
      }
    }

    // 处理末尾未被 \n\n 分隔的残余数据
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6)
        try {
          const parsed = JSON.parse(data)
          if (parsed.type !== 'done') onChunk(parsed)
        } catch { /* ignore */ }
      }
    }
  })
}

export function createSession(user_id, session_title) {
  return request.post('/api/chat/create-session', { user_id, session_title })
}

export function listSessions(user_id, limit = 20) {
  return request.post('/api/chat/sessions', { user_id, limit })
}

export function listMessages(session_id) {
  return request.post('/api/chat/messages', { session_id })
}

export function appendUserMessage(session_id, content, stock_code = null) {
  return request.post('/api/chat/append-user-message', { session_id, content, stock_code })
}

export function appendAssistantMessage(session_id, content, stock_code = null) {
  return request.post('/api/chat/append-assistant-message', { session_id, content, stock_code })
}

export function updateCurrentStock(session_id, stock_code) {
  return request.post('/api/chat/update-current-stock', { session_id, stock_code })
}

export function deleteSession(session_id) {
  return request.post('/api/chat/delete-session', { session_id })
}

>>>>>>> Stashed changes
export function uploadPDF(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  return request.post('/api/upload_pdf', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: progressEvent => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(percent)
      }
    }
  })
}

// POST /api/agent/stream — 真正的 ReAct Agent 流式接口
export function sendAgentStream(payload, onEvent) {
  return fetch('/api/agent/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(async (response) => {
    if (!response.ok) {
      let errText = ''
      try { errText = await response.text() } catch { /* ignore */ }
      throw new Error(errText || `服务器错误 (${response.status})`)
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop()
      for (const part of parts) {
        for (const line of part.split('\n')) {
          if (line.startsWith('data: ')) {
            try { onEvent(JSON.parse(line.slice(6))) } catch { /* ignore */ }
          }
        }
      }
    }
    if (buffer.trim()) {
      for (const line of buffer.split('\n')) {
        if (line.startsWith('data: ')) {
          try { onEvent(JSON.parse(line.slice(6))) } catch { /* ignore */ }
        }
      }
    }
  })
}
