import request from './request'

export function getDocPreview({ doc_type, stock_code = '', industry_code = '', publish_date = '', news_uid = '', source_url = '' }) {
  const params = new URLSearchParams({ doc_type, stock_code, industry_code, publish_date, news_uid, source_url })
  return request.get(`/api/doc/preview?${params}`)
}
