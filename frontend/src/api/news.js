import request from './request'

export function getNewsByCompany(stock_code, days = 30) {
  return request.post('/api/news/by-company', { stock_code, days })
}

export function getNewsByIndustry(industry_code, days = 30) {
  return request.post('/api/news/by-industry', { industry_code, days })
}

export function getNewsImpactSummary(stock_code = null, industry_code = null, days = 30) {
  return request.post('/api/news/impact-summary', { stock_code, industry_code, days })
}

export function getReportsByIndustry(industry_code, days = 30) {
  return request.post('/api/news/reports-by-industry', { industry_code, days })
}

export function getCompanyNewsImpact(stock_code, days = 30) {
  return request.post('/api/news/company-impact', { stock_code, days })
}
