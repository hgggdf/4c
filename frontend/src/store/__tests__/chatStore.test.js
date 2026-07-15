import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { buildSessionTitle, useChatStore } from '../chatStore'
import * as chatApi from '../../api/chat'
import * as retrievalApi from '../../api/retrieval'

vi.mock('../../api/chat', () => ({
  sendChatMessageStream: vi.fn(),
  sendAgentStream: vi.fn(),
  createSession: vi.fn(),
  listSessions: vi.fn(),
  listMessages: vi.fn(),
  appendUserMessage: vi.fn(),
  appendAssistantMessage: vi.fn(),
  updateSessionTitle: vi.fn(),
  deleteSession: vi.fn(),
}))

vi.mock('../../api/retrieval', () => ({
  searchHybrid: vi.fn(),
}))

describe('chatStore.js — ask() 方法触发链路', () => {
  let store

  beforeEach(async () => {
    setActivePinia(createPinia())
    chatApi.createSession.mockResolvedValue({ id: 1, session_title: '测试会话' })
    chatApi.appendUserMessage.mockResolvedValue({})
    chatApi.appendAssistantMessage.mockResolvedValue({})
    chatApi.updateSessionTitle.mockResolvedValue({})
    retrievalApi.searchHybrid.mockResolvedValue({ data: { items: [] } })
    store = useChatStore()
    // 创建新会话以便测试
    await store.newSession()
    vi.clearAllMocks()
  })

  it('调用 ask() 时添加空的 assistant 消息', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    const initialCount = store.messages.length
    await store.ask({ message: '测试' })

    expect(store.messages.length).toBe(initialCount + 2)
    const assistantMsg = store.messages[store.messages.length - 1]
    expect(assistantMsg.role).toBe('assistant')
    expect(assistantMsg.content).toBe('')
    expect(assistantMsg.createdAt).toBeTypeOf('number')
  })

  it('首条问题会自动生成并持久化会话标题', async () => {
    store.activeSession.title = '新对话'
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({
      message: '对比研发投入和核心产品管线',
      targets: [{ symbol: '600276', name: '恒瑞医药', type: 'stock' }],
    })

    expect(store.activeSession.title).toBe('恒瑞医药：对比研发投入和核心产品管线')
    expect(chatApi.updateSessionTitle).toHaveBeenCalledWith(
      store.activeSessionId,
      '恒瑞医药：对比研发投入和核心产品管线',
    )
  })

  it('后续问题不会覆盖已有会话标题', async () => {
    store.activeSession.title = '新对话'
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({ message: '第一个问题' })
    await store.ask({ message: '第二个问题' })

    expect(store.activeSession.title).toBe('第一个问题')
    expect(chatApi.updateSessionTitle).toHaveBeenCalledTimes(1)
  })

  it('当前会话为空时不会重复创建空白会话', async () => {
    const sessionCount = store.sessions.length

    await store.newSession()

    expect(store.sessions).toHaveLength(sessionCount)
    expect(chatApi.createSession).not.toHaveBeenCalled()
  })

  it('手动重命名会话并持久化', async () => {
    chatApi.updateSessionTitle.mockResolvedValue({ session_title: '恒瑞医药风险复盘' })

    const success = await store.renameSession(store.activeSessionId, '  恒瑞医药风险复盘  ')

    expect(success).toBe(true)
    expect(store.activeSession.title).toBe('恒瑞医药风险复盘')
    expect(chatApi.updateSessionTitle).toHaveBeenCalledWith(store.activeSessionId, '恒瑞医药风险复盘')
  })

  it('Agent 模式只新增标题上下文，不改变实际提问内容', async () => {
    store.activeSession.title = '新对话'
    chatApi.sendAgentStream.mockResolvedValue(undefined)
    const message = '[标的: 恒瑞医药(600276)] 分析核心产品管线'

    await store.askAgent({
      message,
      titleMessage: '分析核心产品管线',
      targets: [{ symbol: '600276', name: '恒瑞医药', type: 'stock' }],
    })

    expect(store.activeSession.title).toBe('恒瑞医药：分析核心产品管线')
    expect(chatApi.sendAgentStream.mock.calls[0][0].message).toBe(message)
  })

  it('调用流式 API sendChatMessageStream', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({ message: '查看趋势', targets: [] })

    expect(chatApi.sendChatMessageStream).toHaveBeenCalledOnce()
    const [payload, onChunk] = chatApi.sendChatMessageStream.mock.calls[0]

    expect(payload.message).toBe('查看趋势')
    expect(payload.targets).toEqual([])
    expect(payload.history).toBeInstanceOf(Array)
    expect(onChunk).toBeTypeOf('function')
  })

  it('逐块更新 assistant 消息内容', async () => {
    chatApi.sendChatMessageStream.mockImplementation((payload, onChunk) => {
      onChunk({ type: 'answer_chunk', content: 'Hello' })
      onChunk({ type: 'answer_chunk', content: ' ' })
      onChunk({ type: 'answer_chunk', content: 'World' })
      return Promise.resolve()
    })

    await store.ask({ message: '测试' })

    const assistantMsg = store.messages[store.messages.length - 1]
    expect(assistantMsg.content).toBe('Hello World')
  })

  it('answer_chunk.content 为空时不更新内容', async () => {
    chatApi.sendChatMessageStream.mockImplementation((payload, onChunk) => {
      onChunk({ type: 'answer_chunk', content: 'Start' })
      onChunk({ type: 'done' })
      onChunk({ type: 'answer_chunk', content: '' })
      onChunk({ type: 'answer_chunk', content: ' End' })
      return Promise.resolve()
    })

    await store.ask({ message: '测试' })

    const assistantMsg = store.messages[store.messages.length - 1]
    expect(assistantMsg.content).toBe('Start End')
  })

  it('请求失败时 loading 恢复为 false', async () => {
    chatApi.sendChatMessageStream.mockRejectedValue(new Error('网络错误'))

    await store.ask({ message: '测试' })

    expect(store.loading).toBe(false)
  })

  it('请求失败时在 assistant 消息中追加错误提示', async () => {
    chatApi.sendChatMessageStream.mockRejectedValue(new Error('连接超时'))

    await store.ask({ message: '测试' })

    const assistantMsg = store.messages[store.messages.length - 1]
    expect(assistantMsg.content).toContain('[请求失败：连接超时]')
  })

  it('传入 targets 但无 message 时，content 自动生成联合分析提示', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({
      message: '',
      targets: [
        { symbol: '600276', name: '恒瑞医药', type: 'stock' },
        { symbol: '000661', name: '长春高新', type: 'stock' },
      ],
    })

    const [payload] = chatApi.sendChatMessageStream.mock.calls[0]
    expect(payload.message).toBe('请对以下标的进行联合分析：恒瑞医药、长春高新')
  })

  it('传入 targets 和 message 时，在 message 前添加联合分析标签', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({
      message: '对比研发投入',
      targets: [
        { symbol: '600276', name: '恒瑞医药', type: 'stock' },
        { symbol: '000661', name: '长春高新', type: 'stock' },
      ],
    })

    const [payload] = chatApi.sendChatMessageStream.mock.calls[0]
    expect(payload.message).toBe('[联合分析：恒瑞医药、长春高新] 对比研发投入')
  })

  it('history 包含之前的所有消息（不含当前 assistant 消息）', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    // 第一轮对话
    await store.ask({ message: '第一个问题' })

    // 第二轮对话
    await store.ask({ message: '第二个问题' })

    const [payload] = chatApi.sendChatMessageStream.mock.calls[1]
    expect(payload.history.length).toBeGreaterThan(0)

    // history 应该包含初始消息 + 第一轮的 assistant
    const historyRoles = payload.history.map(m => m.role)
    expect(historyRoles).toContain('assistant')
  })

  it('history 中的消息只包含 role 和 content 字段', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    await store.ask({ message: '测试', targets: [{ symbol: '600276', name: '恒瑞医药' }] })

    const [payload] = chatApi.sendChatMessageStream.mock.calls[0]
    payload.history.forEach(msg => {
      expect(msg).toHaveProperty('role')
      expect(msg).toHaveProperty('content')
      expect(msg).not.toHaveProperty('targets')
      expect(msg).not.toHaveProperty('createdAt')
    })
  })

  it('多次调用 ask() 累积消息', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    const initialCount = store.messages.length

    await store.ask({ message: '问题1' })
    await store.ask({ message: '问题2' })
    await store.ask({ message: '问题3' })

    expect(store.messages.length).toBe(initialCount + 6) // 每次 ask 添加 1 条 user + 1 条 assistant 消息
  })

  it('流式响应中途出错，已接收的内容保留', async () => {
    let chunkCallback
    chatApi.sendChatMessageStream.mockImplementation((payload, onChunk) => {
      chunkCallback = onChunk
      chunkCallback({ type: 'answer_chunk', content: '部分内容' })
      return Promise.reject(new Error('中断'))
    })

    await store.ask({ message: '测试' })

    const assistantMsg = store.messages[store.messages.length - 1]
    expect(assistantMsg.content).toContain('部分内容')
    expect(assistantMsg.content).toContain('[请求失败：中断]')
  })

  it('targets 参数正确传递给 API', async () => {
    chatApi.sendChatMessageStream.mockResolvedValue(undefined)

    const targets = [{ symbol: '600276', name: '恒瑞医药', type: 'stock' }]
    await store.ask({ message: '分析', targets })

    const [payload] = chatApi.sendChatMessageStream.mock.calls[0]
    expect(payload.targets).toEqual(targets)
  })
})

describe('buildSessionTitle()', () => {
  it('自动标题最多 24 个字符', () => {
    const title = buildSessionTitle({ message: '这是一个用于验证自动会话标题长度限制的非常非常长的问题内容' })

    expect(Array.from(title)).toHaveLength(24)
    expect(title.endsWith('…')).toBe(true)
  })

  it('没有文本时根据分析标的命名', () => {
    const title = buildSessionTitle({
      targets: [
        { name: '恒瑞医药' },
        { name: '百济神州' },
      ],
    })

    expect(title).toBe('恒瑞医药、百济神州联合分析')
  })
})
