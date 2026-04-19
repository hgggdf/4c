import { defineStore } from 'pinia'
import { sendChatMessage } from '../api/chat'

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
  },
})
