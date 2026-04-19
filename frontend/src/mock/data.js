// mock 数据 — 后端就绪后替换为真实 API 调用

export const MOCK_STOCKS = [
  { symbol: '600276', name: '恒瑞医药',   price: 42.58, change: 1.23,  change_pct: 2.97,  industry: '化学制药',   pe: 38.2,  pb: 4.1 },
  { symbol: '300759', name: '康龙化成',   price: 31.20, change: -0.45, change_pct: -1.42, industry: 'CRO',        pe: 25.1,  pb: 3.8 },
  { symbol: '002390', name: '信立泰',     price: 15.60, change: 0.30,  change_pct: 1.96,  industry: '化学制药',   pe: 22.4,  pb: 2.6 },
  { symbol: '600196', name: '复星医药',   price: 21.80, change: -0.60, change_pct: -2.68, industry: '生物制药',   pe: 18.7,  pb: 1.9 },
  { symbol: '300347', name: '泰格医药',   price: 55.40, change: 2.10,  change_pct: 3.94,  industry: 'CRO',        pe: 30.2,  pb: 4.5 },
  { symbol: '600436', name: '片仔癀',     price: 218.0, change: 3.80,  change_pct: 1.77,  industry: '中药',       pe: 45.6,  pb: 12.3 },
  { symbol: '000538', name: '云南白药',   price: 58.30, change: -1.20, change_pct: -2.02, industry: '中药',       pe: 24.3,  pb: 3.2 },
  { symbol: '688180', name: '君实生物',   price: 28.90, change: 0.90,  change_pct: 3.21,  industry: '生物制药',   pe: null,  pb: 5.8 },
  { symbol: '300122', name: '智飞生物',   price: 35.60, change: -0.80, change_pct: -2.20, industry: '生物制品',   pe: 19.1,  pb: 3.4 },
  { symbol: '600330', name: '天通股份',   price: 10.25, change: 0.15,  change_pct: 1.48,  industry: '医疗器械',   pe: 31.5,  pb: 2.1 },
  { symbol: '300760', name: '迈瑞医疗',   price: 185.0, change: 4.50,  change_pct: 2.49,  industry: '医疗器械',   pe: 28.4,  pb: 6.7 },
  { symbol: '688321', name: '荣昌生物',   price: 22.10, change: -0.30, change_pct: -1.34, industry: '生物制药',   pe: null,  pb: 4.2 },
]

export const MOCK_INDUSTRIES = [
  { name: '化学制药', code: 'pharma',   count: 48, change_pct: 1.42,  leader: '恒瑞医药', heat: 0.72 },
  { name: 'CRO',     code: 'cro',      count: 16, change_pct: 2.18,  leader: '药明康德', heat: 0.88 },
  { name: '生物制药', code: 'biotech',  count: 35, change_pct: -0.85, leader: '复星医药', heat: 0.65 },
  { name: '医疗器械', code: 'device',   count: 62, change_pct: 0.91,  leader: '迈瑞医疗', heat: 0.79 },
  { name: '中药',    code: 'tcm',      count: 29, change_pct: -1.23, leader: '片仔癀',   heat: 0.54 },
  { name: '生物制品', code: 'bioproduct',count:18, change_pct: 3.05,  leader: '智飞生物', heat: 0.91 },
  { name: '医疗服务', code: 'service',  count: 22, change_pct: 0.30,  leader: '爱尔眼科', heat: 0.60 },
  { name: '化学原料药',code:'rawmat',   count: 31, change_pct: -0.52, leader: '华海药业', heat: 0.48 },
]

export const MOCK_MACRO_SERIES = {
  CPI: {
    label: 'CPI 同比 (%)',
    dates:  ['2024-01','2024-02','2024-03','2024-04','2024-05','2024-06',
             '2024-07','2024-08','2024-09','2024-10','2024-11','2024-12'],
    values: [0.7, 0.7, 0.1, 0.3, 0.3, 0.2, 0.5, 0.6, 0.4, 0.3, 0.2, 0.1],
  },
  PPI: {
    label: 'PPI 同比 (%)',
    dates:  ['2024-01','2024-02','2024-03','2024-04','2024-05','2024-06',
             '2024-07','2024-08','2024-09','2024-10','2024-11','2024-12'],
    values: [-2.5,-2.7,-2.8,-2.5,-2.8,-0.8,-0.8,-1.8,-2.8,-2.9,-2.5,-2.3],
  },
  PMI: {
    label: 'PMI 制造业',
    dates:  ['2024-01','2024-02','2024-03','2024-04','2024-05','2024-06',
             '2024-07','2024-08','2024-09','2024-10','2024-11','2024-12'],
    values: [49.2, 49.1, 50.8, 50.4, 49.5, 49.5, 49.4, 49.1, 49.8, 50.1, 50.3, 50.1],
  },
  社融: {
    label: '社融存量同比 (%)',
    dates:  ['2024-01','2024-02','2024-03','2024-04','2024-05','2024-06',
             '2024-07','2024-08','2024-09','2024-10','2024-11','2024-12'],
    values: [9.5, 9.0, 8.7, 8.3, 8.4, 8.1, 8.2, 8.1, 8.0, 7.8, 7.8, 8.0],
  },
  GDP: {
    label: 'GDP 同比增速 (%)',
    dates:  ['2023Q1','2023Q2','2023Q3','2023Q4','2024Q1','2024Q2','2024Q3','2024Q4'],
    values: [4.5, 6.3, 4.9, 5.2, 5.3, 4.7, 4.6, 5.0],
  },
  医药研发投入: {
    label: '医药行业研发投入增速 (%)',
    dates:  ['2020','2021','2022','2023','2024'],
    values: [18.2, 22.5, 19.8, 15.3, 16.7],
  },
}

export const MOCK_REPORTS = [
  { id: 1, title: '恒瑞医药 2024 年年报深度解读：创新药管线持续兑现', broker: '中信证券', analyst: '贺菊颖', date: '2025-03-20', rating: '买入', target: 50.0 },
  { id: 2, title: 'CRO 行业 2025 年展望：国际化加速，头部效应显现',   broker: '华泰证券', analyst: '代雯',   date: '2025-01-15', rating: '增持', target: null },
  { id: 3, title: '迈瑞医疗：海外收入超预期，器械国产替代进入加速期',  broker: '国泰君安', analyst: '唐爱金', date: '2025-03-28', rating: '买入', target: 220.0 },
  { id: 4, title: '中药板块月报：政策持续支持，龙头估值修复空间充足',  broker: '招商证券', analyst: '许菲菲', date: '2025-04-02', rating: '中性', target: null },
  { id: 5, title: '智飞生物 Q1 业绩前瞻：结合疫苗放量，关注代理品种',  broker: '东方证券', analyst: '吴斌',   date: '2025-04-10', rating: '增持', target: 42.0 },
]

export const MOCK_STOCK_METRICS = {
  '600276': { 营收: '22.4B', 净利润: '4.2B', ROE: '11.3%', 毛利率: '85.2%', 负债率: '28.1%', 研发占比: '12.8%', 市值: '268B', 管线数量: 52 },
  '300760': { 营收: '34.1B', 净利润: '8.1B', ROE: '22.5%', 毛利率: '67.3%', 负债率: '21.4%', 研发占比: '8.9%',  市值: '680B', 管线数量: null },
  default:  { 营收: '--',    净利润: '--',   ROE: '--',    毛利率: '--',    负债率: '--',    研发占比: '--',    市值: '--',  管线数量: null },
}

// K线 mock 数据生成
export function generateKline(symbol, days = 60) {
  const base = { '600276': 38, '300760': 172 }[symbol] || 30
  const result = []
  let price = base
  const now = new Date()
  for (let i = days; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    if (d.getDay() === 0 || d.getDay() === 6) continue
    const open  = price
    const close = +(price + (Math.random() - 0.48) * price * 0.025).toFixed(2)
    const high  = +(Math.max(open, close) * (1 + Math.random() * 0.012)).toFixed(2)
    const low   = +(Math.min(open, close) * (1 - Math.random() * 0.012)).toFixed(2)
    const vol   = Math.floor(80000 + Math.random() * 120000)
    result.push({ date: d.toISOString().slice(0,10), open, close, high, low, vol })
    price = close
  }
  return result
}
