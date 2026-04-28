import request from './request'

export function getCompanyBasic(stock_code) {
  return request.get(`/api/company/basic/${stock_code}`)
}

export function getCompanyProfile(stock_code) {
  return request.get(`/api/company/profile/${stock_code}`)
}

export function getCompanyOverview(stock_code) {
  return request.get(`/api/company/overview/${stock_code}`)
}
