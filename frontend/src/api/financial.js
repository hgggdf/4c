import request from './request'

export function getIncomeStatements(stock_code, limit = 4) {
  return request.post('/api/financial/income-statements', { stock_code, limit })
}

export function getBalanceSheets(stock_code, limit = 4) {
  return request.post('/api/financial/balance-sheets', { stock_code, limit })
}

export function getCashflowStatements(stock_code, limit = 4) {
  return request.post('/api/financial/cashflow-statements', { stock_code, limit })
}

export function getFinancialMetrics(stock_code, metric_names = [], limit = 4) {
  return request.post('/api/financial/metrics', { stock_code, metric_names, limit })
}

export function getBusinessSegments(stock_code, limit = 4) {
  return request.post('/api/financial/business-segments', { stock_code, limit })
}

export function getFinancialSummary(stock_code, period_count = 4) {
  return request.post('/api/financial/summary', { stock_code, period_count })
}
