import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

export function formatDateTime(timestamp) {
  if (!timestamp) return '--'
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', { hour12: false })
}

<<<<<<< Updated upstream
=======
export function formatAssistantContent(content) {
  if (!content) return ''
  return String(content).replace(/\r\n/g, '\n')
}

export function renderMarkdown(content) {
  if (!content) return ''
  const html = marked.parse(String(content).replace(/\r\n/g, '\n'))
  return DOMPurify.sanitize(html)
}

>>>>>>> Stashed changes
export function getChangeClass(value) {
  const num = Number(value)
  if (Number.isNaN(num)) return ''
  if (num > 0) return 'red'
  if (num < 0) return 'green'
  return ''
}
