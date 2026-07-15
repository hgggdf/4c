import { defineStore } from 'pinia'
import {
  sendChatMessageStream,
  sendAgentStream,
  createSession,
  listSessions,
  listMessages,
  appendUserMessage,
  appendAssistantMessage,
  updateSessionTitle,
  deleteSession as deleteChatSession,
} from '../api/chat'
import { searchHybrid } from '../api/retrieval'

const WELCOME_MSG = '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据'
const DEFAULT_SESSION_TITLE = '新对话'
const AUTO_TITLE_MAX_LENGTH = 24
const MANUAL_TITLE_MAX_LENGTH = 50

const MODE_TITLES = {
  company_analysis: '企业运营评估',
  financial_analysis: '财务分析',
  butterfly_analysis: '蝴蝶效应分析',
  risk_analysis: '风险分析',
  pipeline_analysis: '研发管线分析',
}

function normalizeTitleText(value) {
  return String(value || '')
    .replace(/\[([^\]]+)]\([^)]+\)/g, '$1')
    .replace(/https?:\/\/\S+/gi, '')
    .replace(/[`#>*_~]/g, ' ')
    .replace(/[\r\n\t]+/g, ' ')
    .replace(/\s+/g, ' ')
    .replace(/^[：:，,；;。.!！?？\s-]+|[：:，,；;。.!！?？\s-]+$/g, '')
    .trim()
}

function truncateTitle(value, maxLength) {
  const characters = Array.from(value)
  if (characters.length <= maxLength) return value
  return `${characters.slice(0, maxLength - 1).join('')}…`
}

export function buildSessionTitle({ message = '', targets = [], selectedMode = null } = {}) {
  const targetNames = [...new Set(targets.map(item => normalizeTitleText(item?.name)).filter(Boolean))]
  const question = normalizeTitleText(message)
  let title = ''

  if (targetNames.length && question) {
    title = `${targetNames.join('、')}：${question}`
  } else if (question) {
    title = question
  } else if (targetNames.length > 1) {
    title = `${targetNames.join('、')}联合分析`
  } else if (targetNames.length === 1) {
    title = `${targetNames[0]}分析`
  } else if (selectedMode) {
    title = MODE_TITLES[selectedMode] || normalizeTitleText(selectedMode)
  }

  return truncateTitle(title || DEFAULT_SESSION_TITLE, AUTO_TITLE_MAX_LENGTH)
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    activeSessionId: null,
    loading: false,
    sessionLoading: {},
    sessionsLoaded: false,
    pendingClarification: null,   // { question, suggestions, sessionId }
    featureMode: null,
  }),
  getters: {
    activeSession(state) {
      return state.sessions.find(s => s.id === state.activeSessionId) || state.sessions[0]
    },
    messages(state) {
      return state.sessions.find(s => s.id === state.activeSessionId)?.messages || []
    },
    isSessionLoading: (state) => (sessionId) => !!state.sessionLoading[sessionId],
  },
  actions: {
    async loadSessions() {
      if (this.sessionsLoaded) return
      try {
        const items = await listSessions(1, 20)
        const list = Array.isArray(items) ? items : []
        this.sessions = list.map(s => ({
          id: s.id ?? s.session_id,
          title: s.session_title || s.title || DEFAULT_SESSION_TITLE,
          preview: '',
          updatedAt: (s.updated_at || s.created_at || '').slice(0, 10),
          messages: [],
        }))
        this.sessionsLoaded = true
        if (this.sessions.length) {
          this.activeSessionId = this.sessions[0].id
          await this.loadMessages(this.sessions[0].id)
        } else {
          await this.newSession()
        }
      } catch (err) {
        console.error('[loadSessions]', err)
        this.sessionsLoaded = true
        await this.newSession()
      }
    },

    async loadMessages(sessionId) {
      try {
        const items = await listMessages(sessionId)
        const list = Array.isArray(items) ? items : []
        const session = this.sessions.find(s => s.id === sessionId)
        if (session) {
          session.messages = list.map(m => ({
            role: m.role,
            content: m.content,
            createdAt: m.created_at ? new Date(m.created_at).getTime() : Date.now(),
            toolCalls: m.tool_calls_json?.retrieval_trace || m.tool_calls_json || [],
            retrievalTrace: m.tool_calls_json?.retrieval_trace || [],
          }))
          if (!session.messages.length) {
            session.messages.push({ role: 'assistant', content: WELCOME_MSG, createdAt: Date.now() })
          }
          const firstUserMessage = session.messages.find(message => message.role === 'user')
          if (session.title === DEFAULT_SESSION_TITLE && firstUserMessage) {
            this.autoNameSession(session.id, { message: firstUserMessage.content })
          }
        }
      } catch (err) {
        console.error('[loadMessages]', err)
      }
    },

    async switchSession(id) {
      this.activeSessionId = id
      const session = this.sessions.find(s => s.id === id)
      if (session && session.messages.length === 0) {
        await this.loadMessages(id)
      }
    },

    switchMode(mode) {
      this.featureMode = mode
    },

    async deleteSession(sessionId) {
      try {
        await deleteChatSession(sessionId)
        delete this.sessionLoading[sessionId]
        this.sessions = this.sessions.filter(s => s.id !== sessionId)
        if (this.activeSessionId === sessionId) {
          this.activeSessionId = this.sessions[0]?.id || null
          if (!this.activeSessionId) {
            await this.newSession()
          }
        }
        this.loading = Object.values(this.sessionLoading).some(Boolean)
      } catch (err) {
        console.error('[deleteSession]', err)
      }
    },

    async newSession() {
      const currentSession = this.sessions.find(session => session.id === this.activeSessionId)
      if (currentSession && !currentSession.messages.some(message => message.role === 'user')) {
        return currentSession
      }

      try {
        const res = await createSession(1, DEFAULT_SESSION_TITLE)
        const s = res || {}
        const session = {
          id: s.id ?? s.session_id ?? Date.now(),
          title: s.session_title || DEFAULT_SESSION_TITLE,
          preview: '',
          updatedAt: new Date().toISOString().slice(0, 10),
          messages: [{ role: 'assistant', content: WELCOME_MSG, createdAt: Date.now() }],
        }
        this.sessions.unshift(session)
        this.activeSessionId = session.id
        appendAssistantMessage(session.id, WELCOME_MSG).catch(() => {})
      } catch (err) {
        console.error('[newSession]', err)
        const id = Date.now()
        this.sessions.unshift({
          id,
          title: DEFAULT_SESSION_TITLE,
          preview: '',
          updatedAt: new Date().toISOString().slice(0, 10),
          messages: [{ role: 'assistant', content: WELCOME_MSG, createdAt: Date.now() }],
        })
        this.activeSessionId = id
      }
    },

    autoNameSession(sessionId, context) {
      const session = this.sessions.find(item => item.id === sessionId)
      if (!session || session.title !== DEFAULT_SESSION_TITLE) return

      const title = buildSessionTitle(context)
      if (title === DEFAULT_SESSION_TITLE) return

      session.title = title
      session.updatedAt = new Date().toISOString().slice(0, 10)
      updateSessionTitle(sessionId, title).catch(err => {
        console.error('[autoNameSession]', err)
      })
    },

    async renameSession(sessionId, value) {
      const session = this.sessions.find(item => item.id === sessionId)
      const title = normalizeTitleText(value)
      if (!session || !title || Array.from(title).length > MANUAL_TITLE_MAX_LENGTH) return false

      const previousTitle = session.title
      session.title = title
      try {
        const updated = await updateSessionTitle(sessionId, title)
        session.title = updated?.session_title || title
        session.updatedAt = new Date().toISOString().slice(0, 10)
        return true
      } catch (err) {
        session.title = previousTitle
        console.error('[renameSession]', err)
        return false
      }
    },

    async ask({ message, targets = [], selected_mode = null, tool_autonomy = false }) {
      let content = message
      const selectedMode = selected_mode || this.featureMode
      if (!content && selectedMode) {
        content = `请执行【${selectedMode}】功能`
      }
      if (targets.length && !message) {
        content = `请对以下标的进行联合分析：${targets.map(t => t.name).join('、')}`
      } else if (targets.length) {
        content = `[联合分析：${targets.map(t => t.name).join('、')}] ${message}`
      }

      const sessionId = this.activeSessionId
      const session = this.sessions.find(s => s.id === sessionId)
      if (!session || !sessionId) return

      const isFirstQuestion = !session.messages.some(item => item.role === 'user')
      if (isFirstQuestion) {
        this.autoNameSession(sessionId, { message, targets, selectedMode })
      }
      session.updatedAt = new Date().toISOString().slice(0, 10)

      const userMsg = { role: 'user', content, createdAt: Date.now(), sessionId, selectedMode }
      const assistantMsg = {
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        retrievalTrace: [],
        toolEvents: [],
        docPreviews: [],
        followUp: null,
        rnpvResult: null,
        modeTitle: selectedMode,
        sessionId,
        selectedMode,
      }
      session.messages.push(userMsg)
      session.messages.push(assistantMsg)
      // 持有响应式引用
      const reactiveMsg = session.messages[session.messages.length - 1]
      this.sessionLoading[sessionId] = true
      this.loading = Object.values(this.sessionLoading).some(Boolean)

      appendUserMessage(sessionId, content).catch(() => {})

      try {
        // 宏观/事件驱动模式（如蝴蝶效应）分析的是宏观事件与行业传导，没有特定公司。
        // 此处的公司级预检索无相关性下限，会硬凑 top-k 命中知识库里占比最高的公司
        // （如恒瑞医药）并拼进 prompt，导致分析跑偏。这类模式跳过预检索拼接。
        const MACRO_MODES = ['butterfly_analysis']
        const isMacroMode = MACRO_MODES.includes(selectedMode)

        const retrievalRes = isMacroMode ? null : await searchHybrid({
          query: content,
          stock_code: targets.find(t => t.type !== 'industry')?.symbol || null,
          industry_code: targets.find(t => t.type === 'industry')?.symbol || null,
          top_k: 5,
        }).catch(() => null)
        const retrievalItems = retrievalRes?.data?.items ?? retrievalRes?.items ?? []
        reactiveMsg.retrievalTrace = retrievalItems.slice(0, 5)
        const contextText = retrievalItems.slice(0, 3).map((item, index) => {
          const title = item?.metadata?.title || item?.source_record?.title || '未命名结果'
          const snippet = item?.text || item?.source_record?.summary_text || item?.source_record?.content || ''
          const source = item?.match_source || 'vector'
          return `【检索${index + 1}｜${source}｜${title}】${snippet}`
        }).join('\n')
        const finalMessage = contextText ? `${content}\n\n[参考检索结果]\n${contextText}` : content

        await sendChatMessageStream(
          {
            message: finalMessage,
            targets,
            session_id: sessionId,
            user_id: 1,
            selected_mode: selectedMode,
            tool_autonomy,
            retrieval_context: retrievalItems.slice(0, 5),
            history: session.messages
              .slice(0, -2)
              .map(m => ({ role: m.role, content: m.content })),
          },
          (event) => {
            if (event.type === 'tool_call') {
              reactiveMsg.toolEvents = [...reactiveMsg.toolEvents, { type: 'tool_call', tool: event.tool, args: event.args }]
            } else if (event.type === 'tool_result') {
              reactiveMsg.toolEvents = [...reactiveMsg.toolEvents, { type: 'tool_result', tool: event.tool, preview: event.content || event.preview || '' }]
            } else if (event.type === 'status') {
              reactiveMsg.toolEvents = [...reactiveMsg.toolEvents, { type: 'status', content: event.content }]
            } else if (event.type === 'doc_preview') {
              reactiveMsg.docPreviews = [...reactiveMsg.docPreviews, {
                title: event.title,
                kind: event.kind,
                date: event.date,
                file_name: event.file_name,
                source_url: event.source_url || '',
                summary: event.summary || '',
              }]
            } else if (event.type === 'clarification') {
              reactiveMsg.isClarification = true
              reactiveMsg.content = event.question
              reactiveMsg.clarificationSuggestions = event.suggestions || []
              this.pendingClarification = {
                question: event.question,
                suggestions: event.suggestions || [],
                sessionId,
              }
            } else if (event.type === 'answer') {
              reactiveMsg.content += event.content || ''
              window.dispatchEvent(new CustomEvent('chat-scroll-bottom', { detail: { sessionId } }))
            } else if (event.type === 'answer_chunk') {
              reactiveMsg.content += event.content || ''
              window.dispatchEvent(new CustomEvent('chat-scroll-bottom', { detail: { sessionId } }))
            } else if (event.type === 'synthesizing') {
              reactiveMsg.toolEvents = [...reactiveMsg.toolEvents, { type: 'status', content: '正在综合分析…' }]
            } else if (event.type === 'answer_done') {
              // 流式输出结束标记，无需处理
            } else if (event.type === 'follow_up') {
              reactiveMsg.followUp = event
            } else if (event.type === 'rnpv_result') {
              reactiveMsg.rnpvResult = event.data
            } else if (event.type === 'error') {
              reactiveMsg.content += `\n\n[对话异常: ${event.message || '未知错误'}]`
            } else if (event.type === 'done') {
              // end marker
            }
          }
        )
      } catch (err) {
        const msg = err?.message || String(err) || '未知错误'
        reactiveMsg.content += `\n\n[请求失败：${msg}]`
        console.error('[chatStream error]', err)
      } finally {
        this.sessionLoading[sessionId] = false
        this.loading = Object.values(this.sessionLoading).some(Boolean)
        if (reactiveMsg.content || reactiveMsg.toolEvents.length) {
          appendAssistantMessage(sessionId, reactiveMsg.content || ' ').catch(() => {})
        }
        this.featureMode = null
      }
    },

    // 用户点击功能推荐卡片后调用
    async askFollowUp({ message, stock_code, stock_name, mode }) {
      await this.ask({
        message,
        targets: stock_code ? [{ type: 'stock', symbol: stock_code, name: stock_name || stock_code }] : [],
        selected_mode: mode,
      })
    },

    // 用户回答澄清问题后，带着补充信息重新发问
    async answerClarification(answer) {
      this.pendingClarification = null
      await this.ask({ message: answer })
    },

    // 真正的 ReAct Agent — LLM 自主决定工具链
    async askAgent({ message, titleMessage = message, targets = [] }) {
      const session = this.sessions.find(s => s.id === this.activeSessionId)
      if (!session) return

      const sessionId = this.activeSessionId
      const isFirstQuestion = !session.messages.some(item => item.role === 'user')
      if (isFirstQuestion) {
        this.autoNameSession(sessionId, { message: titleMessage, targets })
      }
      session.updatedAt = new Date().toISOString().slice(0, 10)
      const userMsg = { role: 'user', content: message, createdAt: Date.now() }
      const assistantMsg = {
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        agentTrace: [],
        agentSources: [],
        isAgent: true,
      }
      session.messages.push(userMsg)
      session.messages.push(assistantMsg)
      // 持有响应式引用（Pinia 把 session.messages 转为响应式数组后，末尾元素是响应式对象）
      const reactiveMsg = session.messages[session.messages.length - 1]
      this.sessionLoading[sessionId] = true
      this.loading = true

      appendUserMessage(sessionId, message).catch(() => {})

      try {
        await sendAgentStream(
          { message, session_id: sessionId, history: session.messages.slice(0, -2).map(m => ({ role: m.role, content: m.content })) },
          (event) => {
            if (event.type === 'done') {
              return
            }
            if (event.type === 'thinking') {
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'thinking', content: event.content }]
            } else if (event.type === 'tool_call') {
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'tool_call', tool: event.tool, args: event.args, call_id: event.call_id }]
            } else if (event.type === 'tool_result') {
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'tool_result', tool: event.tool, call_id: event.call_id, source: event.source, preview: event.preview }]
            } else if (event.type === 'status') {
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'status', content: event.content }]
            } else if (event.type === 'answer') {
              reactiveMsg.content = event.content
              reactiveMsg.agentSources = event.sources || []
              window.dispatchEvent(new CustomEvent('chat-scroll-bottom', { detail: { sessionId } }))
            } else if (event.type === 'answer_chunk') {
              reactiveMsg.content += event.content || ''
              window.dispatchEvent(new CustomEvent('chat-scroll-bottom', { detail: { sessionId } }))
            } else if (event.type === 'synthesizing') {
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'status', content: '正在综合分析…' }]
            } else if (event.type === 'answer_done') {
              // end marker
            } else if (event.type === 'clarification') {
              reactiveMsg.content = event.question || '请补充更多信息以便分析。'
              reactiveMsg.agentTrace = [...reactiveMsg.agentTrace, { type: 'status', content: '需要澄清' }]
              window.dispatchEvent(new CustomEvent('chat-scroll-bottom', { detail: { sessionId } }))
            } else if (event.type === 'error') {
              reactiveMsg.content = `[Agent 错误：${event.message}]`
            }
          }
        )
      } catch (err) {
        reactiveMsg.content = `[请求失败：${err?.message || err}]`
      } finally {
        this.sessionLoading[sessionId] = false
        this.loading = Object.values(this.sessionLoading).some(Boolean)
        if (reactiveMsg.content) {
          appendAssistantMessage(sessionId, reactiveMsg.content).catch(() => {})
        }
      }
    },

  },
})
