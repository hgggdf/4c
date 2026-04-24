import request from './request'

// POST /api/chat
export function sendChatMessage(payload) {
  return request.post('/api/chat', payload)
}

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
      // 如果返回的是 HTML 错误页，提取简短信息
      if (errText.includes('<!DOCTYPE') || errText.includes('<html')) {
        errText = `服务器返回 ${response.status} 错误，请确认后端已启动`
      }
      throw new Error(errText || `服务器错误 (${response.status})`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let receivedAny = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        const lines = part.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue
            try {
              const parsed = JSON.parse(data)
              if (parsed.text || parsed.done) {
                receivedAny = true
                onChunk(parsed)
              }
            } catch {
              // ignore malformed JSON
            }
          }
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            if (parsed.text || parsed.done) {
              receivedAny = true
              onChunk(parsed)
            }
          } catch { /* ignore */ }
        }
      }
    }

    if (!receivedAny) {
      throw new Error('服务器返回了空响应，请确认后端正常运行')
    }
  })
}

// POST /api/query/stream (智能问数专用)
export function sendQueryStream(payload, onChunk) {
  return fetch('/api/query/stream', {
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
    let receivedAny = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop()

      for (const part of parts) {
        const lines = part.split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue
            try {
              const parsed = JSON.parse(data)
              receivedAny = true
              onChunk(parsed)
            } catch {
              // ignore malformed JSON
            }
          }
        }
      }
    }

    if (buffer.trim()) {
      const lines = buffer.split('\n')
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          try {
            const parsed = JSON.parse(data)
            receivedAny = true
            onChunk(parsed)
          } catch { /* ignore */ }
        }
      }
    }

    if (!receivedAny) {
      throw new Error('服务器返回了空响应，请确认后端正常运行')
    }
  })
}

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
