import { defineStore } from 'pinia'
import { sendChatMessage } from '../api/chat'

const demoUserId = Number(import.meta.env.VITE_DEMO_USER_ID || 1)

export const useChatStore = defineStore('chat', {
  state: () => ({
    userId: demoUserId,
    messages: [
      {
        role: 'assistant',
        content: '你好，我是智策系统——专注于医药生物行业的智能投资分析助手。\n\n你可以问我：\n• 帮我分析恒瑞医药的研发管线\n• 药明康德最近订单情况怎么样\n• 集采对某某公司的影响有多大\n• 贵州茅台（600519）今天行情如何\n• 医药行业整体趋势分析',
        createdAt: Date.now()
      }
    ],
    loading: false
  }),
  actions: {
    async ask(message) {
      const userMessage = {
        role: 'user',
        content: message,
        createdAt: Date.now()
      }
      this.messages.push(userMessage)
      this.loading = true

      try {
        const response = await sendChatMessage({
          user_id: this.userId,
          message,
          history: this.messages.map(item => ({
            role: item.role,
            content: item.content
          }))
        })

        this.messages.push({
          role: 'assistant',
          content: response.answer,
          createdAt: Date.now(),
          extra: response.quote || null
        })
      } catch (error) {
        this.messages.push({
          role: 'assistant',
          content: `抱歉，处理失败：${error.message}`,
          createdAt: Date.now()
        })
      } finally {
        this.loading = false
      }
    }
  }
})
