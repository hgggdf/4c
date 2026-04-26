import { defineStore } from 'pinia'
<<<<<<< Updated upstream
import { sendChatMessage } from '../api/chat'
=======
import {
  sendChatMessageStream,
  sendAgentStream,
  createSession,
  listSessions,
  listMessages,
  appendUserMessage,
  appendAssistantMessage,
  deleteSession as deleteChatSession,
} from '../api/chat'
import { searchHybrid } from '../api/retrieval'

const WELCOME_MSG = '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据'
>>>>>>> Stashed changes

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [
      {
        role: 'assistant',
        content: '你好，我是医药投研多智能体系统。\n\n你可以：\n• 直接提问，如「分析恒瑞医药的研发管线」\n• 将左侧个股或行业卡片拖入输入框，进行多标的联合分析\n• 切换右侧宏观/行业/个股面板，查看详细数据',
        createdAt: Date.now(),
      }
    ],
    loading: false,
  }),
  actions: {
    async ask({ message, targets = [] }) {
      // 构建用户消息
      let content = message
      if (targets.length && !message) {
        content = `请对以下标的进行联合分析：${targets.map(t => t.name).join('、')}`
      } else if (targets.length) {
        content = `[联合分析：${targets.map(t => t.name).join('、')}] ${message}`
      }

      const userMsg = {
        role: 'user',
        content,
        targets,
        createdAt: Date.now(),
      }
      this.messages.push(userMsg)
      this.loading = true

      try {
<<<<<<< Updated upstream
        const response = await sendChatMessage({
          message: content,
          targets,
          history: this.messages.map(m => ({ role: m.role, content: m.content })),
        })
        this.messages.push({
          role: 'assistant',
          content: response.answer ?? response.message ?? '已收到，正在处理…',
          extra: response.quote || null,
          createdAt: Date.now(),
        })
=======
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
            } else if (event.type === 'error') {
              assistantMsg.content += `\n\n[对话异常: ${event.message || '未知错误'}]`
            } else if (event.type === 'done') {
              // end marker
            }
          }
        )
>>>>>>> Stashed changes
      } catch (err) {
        this.messages.push({
          role: 'assistant',
          content: `抱歉，请求失败：${err.message}`,
          createdAt: Date.now(),
        })
      } finally {
        this.loading = false
      }
    },
<<<<<<< Updated upstream
=======

    // 真正的 ReAct Agent — LLM 自主决定工具链
    async askAgent({ message }) {
      const session = this.sessions.find(s => s.id === this.activeSessionId)
      if (!session) return

      const sessionId = this.activeSessionId
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
      this.sessionLoading[sessionId] = true
      this.loading = true

      appendUserMessage(sessionId, message).catch(() => {})

      try {
        await sendAgentStream(
          { message, session_id: sessionId, history: session.messages.slice(0, -2).map(m => ({ role: m.role, content: m.content })) },
          (event) => {
            if (event.type === 'thinking') {
              assistantMsg.agentTrace.push({ type: 'thinking', content: event.content })
            } else if (event.type === 'tool_call') {
              assistantMsg.agentTrace.push({ type: 'tool_call', tool: event.tool, args: event.args, call_id: event.call_id })
            } else if (event.type === 'tool_result') {
              assistantMsg.agentTrace.push({ type: 'tool_result', tool: event.tool, call_id: event.call_id, source: event.source, preview: event.preview })
            } else if (event.type === 'status') {
              assistantMsg.agentTrace.push({ type: 'status', content: event.content })
            } else if (event.type === 'answer') {
              assistantMsg.content = event.content
              assistantMsg.agentSources = event.sources || []
            } else if (event.type === 'error') {
              assistantMsg.content = `[Agent 错误：${event.message}]`
            }
          }
        )
      } catch (err) {
        assistantMsg.content = `[请求失败：${err?.message || err}]`
      } finally {
        this.sessionLoading[sessionId] = false
        this.loading = Object.values(this.sessionLoading).some(Boolean)
        if (assistantMsg.content) {
          appendAssistantMessage(sessionId, assistantMsg.content).catch(() => {})
        }
      }
    },

>>>>>>> Stashed changes
  },
})
