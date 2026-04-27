import request from './request'

const COMPANY_DATASET_CACHE = new Map()
let stockListPromise = null

const METRIC_FIELD_KEYS = new Set(['选项', '指标'])
const METRIC_MAPPINGS = [
  ['营业总收入', '营业总收入'],
  ['归母净利润', '归母净利润'],
  ['扣非净利润', '扣非净利润'],
  ['净资产收益率(ROE)', '净资产收益率'],
  ['毛利率', '毛利率'],
  ['资产负债率', '资产负债率'],
  ['经营现金流量净额', '经营现金流量净额'],
  ['基本每股收益', '基本每股收益'],
]

function toNumber(value, fallback = 0) {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

function normalizeQuote(quote = {}, fallback = {}) {
  const changePercent = toNumber(
    quote.change_pct ?? quote.change_percent ?? fallback.change_pct ?? fallback.change_percent,
    0
  )

  return {
    symbol: quote.symbol ?? fallback.symbol ?? '',
    name: quote.name ?? fallback.name ?? '',
    price: toNumber(quote.price ?? fallback.price, 0),
    change: toNumber(quote.change ?? fallback.change, 0),
    change_percent: changePercent,
    change_pct: changePercent,
    open: toNumber(quote.open ?? fallback.open, 0),
    high: toNumber(quote.high ?? fallback.high, 0),
    low: toNumber(quote.low ?? fallback.low, 0),
    volume: quote.volume ?? fallback.volume ?? '--',
    time: quote.time ?? fallback.time ?? '--',
  }
}

function normalizeKlinePoint(item = {}) {
  const volume = toNumber(item.volume ?? item.vol, 0)
  return {
    date: item.date ?? '',
    open: toNumber(item.open, 0),
    high: toNumber(item.high, 0),
    low: toNumber(item.low, 0),
    close: toNumber(item.close, 0),
    volume,
    vol: volume,
  }
}

function getLatestMetricEntry(row = {}) {
  return Object.entries(row).find(
    ([key, value]) => !METRIC_FIELD_KEYS.has(key) && value !== null && value !== ''
  )
}

function formatAmount(value) {
  const abs = Math.abs(value)
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (abs >= 1e4) return `${(value / 1e4).toFixed(2)}万`
  return value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function formatMetricValue(metricName, rawValue) {
  const value = Number(rawValue)
  if (!Number.isFinite(value)) return rawValue ?? '--'

  if (metricName.includes('率') || metricName.includes('ROE') || metricName.includes('ROA')) {
    return `${value.toFixed(2)}%`
  }

  if (metricName.includes('每股')) {
    return value.toFixed(2)
  }

  return formatAmount(value)
}

function extractIndustry(dataset = {}) {
  const mainBusiness = Array.isArray(dataset.main_business) ? dataset.main_business : []
  const industryItem =
    mainBusiness.find(
      item => item['分类类型'] === '按行业分类' && item['主营构成'] && !String(item['主营构成']).includes('其他')
    ) ||
    mainBusiness.find(item => item['主营构成'] && !String(item['主营构成']).includes('其他'))

  if (industryItem?.['主营构成']) {
    return industryItem['主营构成']
  }

  const reportItem = Array.isArray(dataset.research_reports)
    ? dataset.research_reports.find(item => item['行业'])
    : null

  return reportItem?.['行业'] || '未分类'
}

function mapCompanyToStock(summary = {}, dataset = null) {
  const quote = normalizeQuote(summary.quote || dataset?.quote, {
    symbol: summary.symbol,
    name: summary.name || dataset?.name,
  })

  return {
    ...quote,
    symbol: summary.symbol || quote.symbol,
    name: summary.name || quote.name || summary.symbol,
    industry: extractIndustry(dataset || {}),
    industry_code: summary.industry_code || null,
    exchange: summary.exchange || dataset?.exchange || '',
    collected_at: summary.collected_at || dataset?.collected_at || '',
  }
}

function mapMetrics(dataset = {}) {
  const rows = Array.isArray(dataset.financial_abstract) ? dataset.financial_abstract : []
  const metrics = {}

  for (const [sourceName, targetName] of METRIC_MAPPINGS) {
    const row = rows.find(item => item['指标'] === sourceName)
    if (!row) continue

    const entry = getLatestMetricEntry(row)
    if (!entry) continue

    metrics[targetName] = formatMetricValue(sourceName, entry[1])
  }

  return metrics
}

function mapReports(dataset = {}, symbol = '') {
  const reports = Array.isArray(dataset.research_reports) ? dataset.research_reports : []
  return reports.slice(0, 12).map((item, index) => ({
    id: `${symbol}-${item['序号'] ?? index}`,
    title: item['报告名称'] || '未命名研报',
    broker: item['机构'] || '--',
    industry: item['行业'] || '',
    date: item['日期'] || '--',
    rating: item['东财评级'] || '未评级',
    target: null,
    pdfUrl: item['报告PDF链接'] || '',
  }))
}

function mapConcepts(dataset = {}) {
  const aliases = Array.isArray(dataset.aliases) ? dataset.aliases : []
  const reports = Array.isArray(dataset.research_reports) ? dataset.research_reports : []
  const industries = [...new Set(reports.map(r => r['行业']).filter(Boolean))]
  return { aliases, industries }
}

function mapEvents(dataset = {}) {
  const anns = Array.isArray(dataset.announcements) ? dataset.announcements : []
  const news = Array.isArray(dataset.news) ? dataset.news : []

  const annEvents = anns.slice(0, 30).map(a => ({
    type: 'announcement',
    title: a['公告标题'] || a['标题'] || '公告',
    category: a['公告类型'] || a['类型'] || '',
    date: a['公告日期'] || a['日期'] || '',
    url: a['来源链接'] || a['网址'] || a['链接'] || '',
  }))

  const newsEvents = news.slice(0, 20).map(n => ({
    type: 'news',
    title: n['新闻标题'] || n['标题'] || '新闻',
    category: n['文章来源'] || n['新闻来源'] || n['来源'] || '',
    date: (n['发布时间'] || n['时间'] || '').slice(0, 10),
    url: n['新闻链接'] || n['链接'] || '',
    summary: n['影响说明'] || n['新闻内容'] || n['摘要'] || '',
  }))

  return [...annEvents, ...newsEvents]
    .filter(e => e.title)
    .sort((a, b) => (b.date > a.date ? 1 : -1))
}

function buildIndustryList(stocks = []) {
  const groups = new Map()

  for (const stock of stocks) {
    const industryName = stock.industry || '未分类'
    const current = groups.get(industryName) || {
      name: industryName,
      code: stock.industry_code || industryName,
      count: 0,
      totalChangePct: 0,
      leader: null,
    }

    current.count += 1
    current.totalChangePct += toNumber(stock.change_pct, 0)

    if (!current.leader || toNumber(stock.price, 0) > toNumber(current.leader.price, 0)) {
      current.leader = stock
    }

    groups.set(industryName, current)
  }

  const maxCount = Math.max(...Array.from(groups.values()).map(item => item.count), 1)

  return Array.from(groups.values())
    .map(item => ({
      name: item.name,
      code: item.code,
      count: item.count,
      change_pct: Number((item.totalChangePct / item.count).toFixed(2)),
      leader: item.leader?.name || '--',
      heat: Number((item.count / maxCount).toFixed(2)),
    }))
    .sort((a, b) => b.count - a.count || b.change_pct - a.change_pct)
}

async function getCompanyDataset(symbol) {
  if (!symbol) return null
  if (COMPANY_DATASET_CACHE.has(symbol)) {
    return COMPANY_DATASET_CACHE.get(symbol)
  }

  const promise = request
    .get('/api/stock/company', { params: { symbol, compact: true } })
    .catch(() => null)

  COMPANY_DATASET_CACHE.set(symbol, promise)
  return promise
}

async function getTrackedStocks() {
  if (!stockListPromise) {
    stockListPromise = request
      .get('/api/stock/companies')
      .then(async companies => {
        const datasets = await Promise.all((companies || []).map(item => getCompanyDataset(item.symbol)))
        return (companies || []).map((item, index) => mapCompanyToStock(item, datasets[index]))
      })
      .catch(error => {
        stockListPromise = null
        throw error
      })
  }

  return stockListPromise
}

// ── 股票列表 ──────────────────────────────────────────
export async function getStockList() {
  return getTrackedStocks()
}

// ── 单只股票行情 ─────────────────────────────────────
export async function getQuote(symbol) {
  const dataset = await getCompanyDataset(symbol)
  if (dataset?.quote) {
    return normalizeQuote(dataset.quote, { symbol, name: dataset.name })
  }

  const quote = await request.get('/api/stock/quote', { params: { symbol } })
  return normalizeQuote(quote, { symbol })
}

// ── K线数据 ───────────────────────────────────────────
export async function getKline(symbol, days = 60) {
  const dataset = await getCompanyDataset(symbol)
  if (Array.isArray(dataset?.kline) && dataset.kline.length) {
    return dataset.kline.slice(-days).map(normalizeKlinePoint)
  }

  const kline = await request.get('/api/stock/kline', { params: { symbol, days } })
  return Array.isArray(kline) ? kline.map(normalizeKlinePoint) : []
}

// ── 股票财务指标 ─────────────────────────────────────
export async function getStockMetrics(symbol) {
  const dataset = await getCompanyDataset(symbol)
  return mapMetrics(dataset)
}

// ── 行业列表 ──────────────────────────────────────────
export async function getIndustryList() {
  const stocks = await getTrackedStocks()
  return buildIndustryList(stocks)
}

// ── 研报列表 ──────────────────────────────────────────
export async function getReports(symbol) {
  const dataset = await getCompanyDataset(symbol)
  return mapReports(dataset, symbol)
}

// ── 概念题材 ──────────────────────────────────────────
export async function getConcepts(symbol) {
  const dataset = await getCompanyDataset(symbol)
  return mapConcepts(dataset)
}

// ── 大事件列表 ────────────────────────────────────────
export async function getEvents(symbol) {
  const dataset = await getCompanyDataset(symbol)
  return mapEvents(dataset)
}

export async function getWatchlist(userId = import.meta.env.VITE_DEMO_USER_ID || 1) {
  return request.get('/api/stock/watchlist', { params: { user_id: userId } })
}

export async function addToWatchlist(symbol, userId = import.meta.env.VITE_DEMO_USER_ID || 1) {
  return request.post('/api/stock/watchlist', { symbol, user_id: userId })
}

export async function removeFromWatchlist(symbol, userId = import.meta.env.VITE_DEMO_USER_ID || 1) {
  return request.delete('/api/stock/watchlist', { params: { symbol, user_id: userId } })
}
