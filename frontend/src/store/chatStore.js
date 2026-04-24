import { defineStore } from 'pinia'
import { sendChatMessageStream } from '../api/chat'

const MOCK_SESSIONS = [
  {
    id: 1,
    title: '恒瑞医药研发管线分析',
    preview: '请分析恒瑞医药的创新药研发管线现状...',
    updatedAt: '2026-04-22',
    messages: [
      { role: 'assistant', content: '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据', createdAt: Date.now() - 8000 },
      { role: 'user', content: '请分析恒瑞医药的创新药研发管线现状', createdAt: Date.now() - 7000 },
      { role: 'assistant', content: '恒瑞医药目前在研管线超过 80 个创新药项目，重点布局肿瘤、自身免疫、代谢等领域。\n\n核心品种包括：\n• SHR-1701（PD-L1/TGF-β双抗）已进入III期\n• HRS-4642（GLP-1/GIP双靶点）减重适应症推进中\n• 马来酸阿伐曲泊帕已获批上市\n\n整体研发投入占营收比例约 23%，处于行业领先水平。', createdAt: Date.now() - 6000 },
    ],
  },
  {
    id: 2,
    title: '眼科医疗板块投资机会',
    preview: '爱尔眼科和华厦眼科的对比分析...',
    updatedAt: '2026-04-21',
    messages: [
      { role: 'assistant', content: '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据', createdAt: Date.now() - 90000 },
      { role: 'user', content: '[联合分析：爱尔眼科、华厦眼科] 对比两家公司的扩张策略和盈利能力', createdAt: Date.now() - 80000 },
      { role: 'assistant', content: '爱尔眼科 vs 华厦眼科对比：\n\n爱尔眼科采用分级连锁模式，门店超 800 家，营收规模约 200 亿，毛利率维持在 45% 以上，扩张以并购为主。\n\n华厦眼科体量较小，约 100 家门店，但单店盈利能力更强，近两年新开店速度加快，成长弹性更大。\n\n综合来看，爱尔更适合稳健型配置，华厦适合成长型布局。', createdAt: Date.now() - 70000 },
    ],
  },
  {
    id: 3,
    title: '集采政策对原料药影响',
    preview: '第八批集采落地后原料药企业的应对...',
    updatedAt: '2026-04-19',
    messages: [
      { role: 'assistant', content: '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据', createdAt: Date.now() - 200000 },
      { role: 'user', content: '第八批集采落地后，原料药企业如何应对价格压力？', createdAt: Date.now() - 190000 },
      { role: 'assistant', content: '第八批集采共纳入 39 个品种，平均降幅约 56%。原料药企业的主要应对策略：\n\n1. 向特色原料药转型，聚焦高壁垒品种\n2. 加大出口比例，规避国内集采压力\n3. 向制剂一体化延伸，提升附加值\n\n华海药业、普洛药业等已在出口端取得明显成效。', createdAt: Date.now() - 180000 },
    ],
  },
  {
    id: 4,
    title: 'GLP-1赛道国内竞争格局',
    preview: '司美格鲁肽国内仿制药进展及竞争...',
    updatedAt: '2026-04-17',
    messages: [
      { role: 'assistant', content: '你好，我是医药投研多智能体系统。', createdAt: Date.now() - 400000 },
      { role: 'user', content: 'GLP-1赛道国内竞争格局如何？', createdAt: Date.now() - 390000 },
      { role: 'assistant', content: '国内 GLP-1 赛道竞争激烈，主要分三个梯队：\n\n第一梯队：华东医药（利拉鲁肽已上市）、信达生物（玛仕度肽III期）\n第二梯队：恒瑞医药、翰宇药业\n第三梯队：多家仿制药企业布局司美格鲁肽\n\n预计2026-2027年将迎来密集获批期，市场竞争将显著加剧。', createdAt: Date.now() - 380000 },
    ],
  },
  {
    id: 5,
    title: '医疗器械出海机会',
    preview: '迈瑞医疗和联影医疗的海外布局...',
    updatedAt: '2026-04-15',
    messages: [
      { role: 'assistant', content: '你好，我是医药投研多智能体系统。', createdAt: Date.now() - 600000 },
      { role: 'user', content: '分析迈瑞医疗和联影医疗的海外扩张策略', createdAt: Date.now() - 590000 },
      { role: 'assistant', content: '迈瑞医疗海外收入占比已超 55%，重点布局欧美高端市场，通过直销+经销商双渠道推进。\n\n联影医疗以高端影像设备为核心，海外市场刚起步，但产品力强，在东南亚和中东市场增速明显。\n\n两者均受益于国产替代和出海双重逻辑。', createdAt: Date.now() - 580000 },
    ],
  },
]

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: MOCK_SESSIONS,
    activeSessionId: 1,
    loading: false,
  }),
  getters: {
    activeSession(state) {
      return state.sessions.find(s => s.id === state.activeSessionId) || state.sessions[0]
    },
    messages(state) {
      return state.sessions.find(s => s.id === state.activeSessionId)?.messages || []
    },
  },
  actions: {
    switchSession(id) {
      this.activeSessionId = id
    },
    newSession() {
      const id = Date.now()
      this.sessions.unshift({
        id,
        title: '新对话',
        preview: '',
        updatedAt: new Date().toISOString().slice(0, 10),
        messages: [
          {
            role: 'assistant',
            content: '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据',
            createdAt: Date.now(),
          },
        ],
      })
      this.activeSessionId = id
    },
    async ask({ message, targets = [] }) {
      let content = message
      if (targets.length && !message) {
        content = `请对以下标的进行联合分析：${targets.map(t => t.name).join('、')}`
      } else if (targets.length) {
        content = `[联合分析：${targets.map(t => t.name).join('、')}] ${message}`
      }

      const session = this.sessions.find(s => s.id === this.activeSessionId)
      if (!session) return

      const assistantMsg = {
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
      }
      this.messages.push(assistantMsg)

      try {
        await sendChatMessageStream(
          {
            message: content,
            targets,
            history: this.messages
              .slice(0, -1)
              .map(m => ({ role: m.role, content: m.content })),
          },
          (chunk) => {
            if (chunk.text) {
              assistantMsg.content += chunk.text
            }
          }
        )
      } catch (err) {
        const msg = err?.message || String(err) || '未知错误'
        assistantMsg.content += `\n\n[请求失败：${msg}]`
        console.error('[chatStream error]', err)
      } finally {
        this.loading = false
      }
    },
  },
})
