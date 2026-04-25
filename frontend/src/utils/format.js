export function formatDateTime(timestamp) {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function formatAssistantContent(content) {
  if (!content) return ''

  return String(content)
    .replace(/\r\n/g, '\n')
    .split('\n')
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => line
      .replace(/^#{1,6}\s*/g, '')
      .replace(/^\*\s+/g, '')
      .replace(/^\d+[.)、]\s*/g, '')
      .replace(/[\*_`]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
    )
    .filter(Boolean)
    .join('\n')
}

export function getChangeClass(value) {
  const num = Number(value)
  if (Number.isNaN(num)) return ''
  if (num > 0) return 'red'
  if (num < 0) return 'green'
  return ''
}
