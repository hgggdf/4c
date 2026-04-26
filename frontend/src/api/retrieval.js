import request from './request'

export function searchHybrid(payload) {
  return request.post('/api/retrieval/hybrid', payload)
}

export function searchAnnouncements(payload) {
  return request.post('/api/retrieval/announcements', payload)
}

export function searchNews(payload) {
  return request.post('/api/retrieval/news', payload)
}

export function searchReports(payload) {
  return request.post('/api/retrieval/reports', payload)
}
