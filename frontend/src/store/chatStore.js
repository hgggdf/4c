import { defineStore } from 'pinia'
import {
  sendChatMessageStream,
  sendQueryStream,
  createSession,
  listSessions,
  listMessages,
  appendUserMessage,
  appendAssistantMessage,
  deleteSession as deleteChatSession,
} from '../api/chat'

const WELCOME_MSG = '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据'

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessions: [],
    activeSessionId: null,
    loading: false,
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
        this.sessions = this.sessions.filter(s => s.id !== sessionId)
        if (this.activeSessionId === sessionId) {
          this.activeSessionId = this.sessions[0]?.id || null
          if (!this.activeSessionId) {
            await this.newSession()
          }
        }
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

    async ask({ message, targets = [] }) {
      let content = message
      const selectedMode = this.featureMode
      if (!content && selectedMode) {
        content = `请执行【${selectedMode}】功能`
      }
      if (targets.length && !message) {
        content = `请对以下标的进行联合分析：${targets.map(t => t.name).join('、')}`
      } else if (targets.length) {
        content = `[联合分析：${targets.map(t => t.name).join('、')}] ${message}`
      }

      const session = this.sessions.find(s => s.id === this.activeSessionId)
      if (!session) return

      const userMsg = { role: 'user', content, createdAt: Date.now() }
      const assistantMsg = { role: 'assistant', content: '', createdAt: Date.now() }
      this.messages.push(userMsg)
      this.messages.push(assistantMsg)
      this.loading = true

      if (this.activeSessionId) {
        appendUserMessage(this.activeSessionId, content).catch(() => {})
      }

      try {
        await sendChatMessageStream(
          {
            message: content,
            targets,
            session_id: this.activeSessionId,
            user_id: 1,
            selected_mode: selectedMode,
            history: this.messages
              .slice(0, -2)
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
        if (this.activeSessionId && assistantMsg.content) {
          appendAssistantMessage(this.activeSessionId, assistantMsg.content).catch(() => {})
        }
        this.featureMode = null
      }
    },

    async askQuery({ message }) {
      const session = this.sessions.find(s => s.id === this.activeSessionId)
      if (!session) return

      const userMsg = { role: 'user', content: message, createdAt: Date.now() }
      const assistantMsg = {
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        toolCalls: [],
        isClarification: false,
      }
      this.messages.push(userMsg)
      this.messages.push(assistantMsg)
      this.loading = true
      this.pendingClarification = false

      if (this.activeSessionId) {
        appendUserMessage(this.activeSessionId, message).catch(() => {})
      }

      try {
        await sendQueryStream(
          {
            message,
            session_id: this.activeSessionId,
            history: this.messages
              .slice(0, -2)
              .map(m => ({ role: m.role, content: m.content })),
          },
          (event) => {
            if (event.type === 'tool_call') {
              assistantMsg.toolCalls.push({
                tool: event.tool,
                args: event.args,
              })
            } else if (event.type === 'tool_result') {
              // 工具结果可选展示
            } else if (event.type === 'status') {
              // 状态更新
            } else if (event.type === 'clarification') {
              assistantMsg.content = event.question
              assistantMsg.isClarification = true
              this.pendingClarification = true
            } else if (event.type === 'answer') {
              assistantMsg.content = event.content
              assistantMsg.isClarification = false
              this.pendingClarification = false
            }
          }
        )
      } catch (err) {
        const msg = err?.message || String(err) || '未知错误'
        assistantMsg.content += `\n\n[请求失败：${msg}]`
        console.error('[queryStream error]', err)
      } finally {
        this.loading = false
        if (this.activeSessionId && assistantMsg.content) {
          appendAssistantMessage(this.activeSessionId, assistantMsg.content).catch(() => {})
        }
      }
    },
  },
})
