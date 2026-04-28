import request from './request'

export function sendButterflyStream(payload, onEvent) {
  return fetch('/api/butterfly/analyze', {
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

export function getButterflyHistory(params = {}) {
  return request.post('/api/butterfly/history', {
    days: params.days || 90,
    event_type: params.event_type || null,
    severity: params.severity || null,
    keyword: params.keyword || null,
    limit: params.limit || 50,
  })
}
