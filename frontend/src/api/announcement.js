import request from './request'

export function getRawAnnouncements(stock_code, days = 365, category = null) {
  return request.post('/api/announcement/raw', { stock_code, days, category })
}

export function getStructuredAnnouncements(stock_code, days = 365, category = null) {
  return request.post('/api/announcement/structured', { stock_code, days, category })
}

export function getDrugApprovals(stock_code, days = 365) {
  return request.post('/api/announcement/drug-approvals', { stock_code, days })
}

export function getClinicalTrials(stock_code, days = 365) {
  return request.post('/api/announcement/clinical-trials', { stock_code, days })
}

export function getProcurementEvents(stock_code, days = 365) {
  return request.post('/api/announcement/procurement-events', { stock_code, days })
}

export function getRegulatoryRisks(stock_code, days = 365) {
  return request.post('/api/announcement/regulatory-risks', { stock_code, days })
}

export function getCompanyEventSummary(stock_code, days = 365) {
  return request.post('/api/announcement/company-event-summary', { stock_code, days })
}
