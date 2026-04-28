import request from './request'

export function getDiagnose(symbol, year = 2024) {
  return request.get('/api/analysis/diagnose', { params: { symbol, year } })
}

export function getRisks(symbols) {
  return request.get('/api/analysis/risks', { params: { symbols } })
}

export function getCompare(metric, year = 2024, symbols) {
  return request.get('/api/analysis/compare', { params: { metric, year, symbols } })
}

export function getTrend(symbol, metric) {
  return request.get('/api/analysis/trend', { params: { symbol, metric } })
}
