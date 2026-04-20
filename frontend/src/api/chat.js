import request from './request'

// POST /api/chat
// payload: { message, targets, history }
export function sendChatMessage(payload) {
  return request.post('/api/chat', payload)
}

// POST /api/upload_pdf
// 上传 PDF 到知识库
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
