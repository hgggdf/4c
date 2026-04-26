import { defineStore } from 'pinia'
import {
  sendChatMessageStream,
  createSession,
  listSessions,
  listMessages,
  appendUserMessage,
  appendAssistantMessage,
  deleteSession as deleteChatSession,
} from '../api/chat'
import { searchHybrid } from '../api/retrieval'

const WELCOME_MSG = '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    activeSessionId: null,
    loading: false,
    sessionLoading: {},
    sessionsLoaded: false,
    pendingClarification: false,
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
          title: s.session_title || s.title || '新对话',
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
      try {
        const res = await createSession(1, '新对话')
        const s = res || {}
        const session = {
          id: s.id ?? s.session_id ?? Date.now(),
          title: s.session_title || '新对话',
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
          title: '新对话',
          preview: '',
          updatedAt: new Date().toISOString().slice(0, 10),
          messages: [{ role: 'assistant', content: WELCOME_MSG, createdAt: Date.now() }],
        })
        this.activeSessionId = id
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

      const userMsg = { role: 'user', content, createdAt: Date.now(), sessionId, selectedMode }
      const assistantMsg = {
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        retrievalTrace: [],
        toolEvents: [],
        modeTitle: selectedMode,
        sessionId,
        selectedMode,
      }
      session.messages.push(userMsg)
      session.messages.push(assistantMsg)
      this.sessionLoading[sessionId] = true
      this.loading = Object.values(this.sessionLoading).some(Boolean)

      appendUserMessage(sessionId, content).catch(() => {})

      try {
        const retrievalRes = await searchHybrid({
          query: content,
          stock_code: targets.find(t => t.type !== 'industry')?.symbol || null,
          industry_code: targets.find(t => t.type === 'industry')?.symbol || null,
          top_k: 5,
        }).catch(() => null)
        const retrievalItems = retrievalRes?.data?.items ?? retrievalRes?.items ?? []
        assistantMsg.retrievalTrace = retrievalItems.slice(0, 5)
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
              assistantMsg.toolEvents.push({ type: 'tool_call', tool: event.tool, args: event.args })
            } else if (event.type === 'tool_result') {
              assistantMsg.toolEvents.push({ type: 'tool_result', tool: event.tool, preview: event.content || event.preview || '' })
            } else if (event.type === 'status') {
              assistantMsg.toolEvents.push({ type: 'status', content: event.content })
            } else if (event.type === 'clarification') {
              assistantMsg.toolEvents.push({ type: 'clarification', question: event.question })
            } else if (event.type === 'answer') {
              assistantMsg.content += event.content || ''
            } else if (event.type === 'done') {
              // end marker
            }
          }
        )
      } catch (err) {
        const msg = err?.message || String(err) || '未知错误'
        assistantMsg.content += `\n\n[请求失败：${msg}]`
        console.error('[chatStream error]', err)
      } finally {
        this.sessionLoading[sessionId] = false
        this.loading = Object.values(this.sessionLoading).some(Boolean)
        if (assistantMsg.content || assistantMsg.toolEvents.length) {
          appendAssistantMessage(sessionId, assistantMsg.content || ' ').catch(() => {})
        }
        this.featureMode = null
      }
    },

  },
})
