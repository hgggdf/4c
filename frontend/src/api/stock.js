import request from './request'

const demoUserId = Number(import.meta.env.VITE_DEMO_USER_ID || 1)

export function getQuote(symbol) {
  return request.get('/api/stock/quote', { params: { symbol } })
}

export function getKline(symbol, days = 30) {
  return request.get('/api/stock/kline', { params: { symbol, days } })
}

export function getWatchlist(userId = demoUserId) {
  return request.get('/api/stock/watchlist', { params: { user_id: userId } })
}
