export function formatDateTime(timestamp) {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function getChangeClass(value) {
  const num = Number(value)
  if (Number.isNaN(num)) return ''
  if (num > 0) return 'red'
  if (num < 0) return 'green'
  return ''
}
