import request from './request'

export function getMacroIndicator(indicator_name, period = null) {
  return request.post('/api/macro/indicator', { indicator_name, period })
}

export function listMacroIndicators(indicator_names, periods = null) {
  return request.post('/api/macro/list', { indicator_names, periods })
}

export function getMacroSummary(indicator_names, recent_n = 6) {
  return request.post('/api/macro/summary', { indicator_names, recent_n })
}
