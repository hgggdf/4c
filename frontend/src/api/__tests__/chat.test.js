import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { sendChatMessage, sendChatMessageStream } from '../chat.js'

// Mock request module
vi.mock('../request.js', () => ({
  default: {
    post: vi.fn(),
  },
}))

describe('chat.js — sendChatMessage (普通聊天)', () => {
  let mockRequest

  beforeEach(async () => {
    mockRequest = (await import('../request.js')).default
    mockRequest.post.mockClear()
  })

  it('调用 request.post("/api/chat", payload)', async () => {
    const payload = { message: 'hello', history: [] }
    mockRequest.post.mockResolvedValue({ reply: 'hi' })

    await sendChatMessage(payload)

    expect(mockRequest.post).toHaveBeenCalledWith('/api/chat', payload)
  })

  it('返回 request.post 的结果', async () => {
    const expected = { reply: 'world' }
    mockRequest.post.mockResolvedValue(expected)

    const result = await sendChatMessage({ message: 'test' })

    expect(result).toEqual(expected)
  })
})

describe('chat.js — sendChatMessageStream (流式聊天)', () => {
  let originalFetch

  beforeEach(() => {
    originalFetch = global.fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
  })

  it('使用原生 fetch() 发送 POST 请求到 /api/chat/stream', async () => {
    const mockFetch = vi.fn()
    global.fetch = mockFetch

    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({ done: false, value: new TextEncoder().encode('data: {"text":"hi"}\n\n') })
        .mockResolvedValueOnce({ done: true }),
    }

    mockFetch.mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const payload = { message: 'test' }
    const onChunk = vi.fn()

    await sendChatMessageStream(payload, onChunk)

    expect(mockFetch).toHaveBeenCalledWith('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
  })

  it('解析 SSE 格式并调用 onChunk', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"text":"hello"}\n\n'),
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"text":" world"}\n\n'),
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"done":true}\n\n'),
        })
        .mockResolvedValueOnce({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const onChunk = vi.fn()
    await sendChatMessageStream({ message: 'test' }, onChunk)

    expect(onChunk).toHaveBeenCalledTimes(3)
    expect(onChunk).toHaveBeenNthCalledWith(1, { text: 'hello' })
    expect(onChunk).toHaveBeenNthCalledWith(2, { text: ' world' })
    expect(onChunk).toHaveBeenNthCalledWith(3, { done: true })
  })

  it('忽略 [DONE] 标记', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"text":"ok"}\n\ndata: [DONE]\n\n'),
        })
        .mockResolvedValueOnce({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const onChunk = vi.fn()
    await sendChatMessageStream({}, onChunk)

    expect(onChunk).toHaveBeenCalledTimes(1)
    expect(onChunk).toHaveBeenCalledWith({ text: 'ok' })
  })

  it('忽略格式错误的 JSON', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {invalid json}\n\ndata: {"text":"valid"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const onChunk = vi.fn()
    await sendChatMessageStream({}, onChunk)

    expect(onChunk).toHaveBeenCalledTimes(1)
    expect(onChunk).toHaveBeenCalledWith({ text: 'valid' })
  })

  it('response.ok 为 false 时抛出错误', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'Internal Server Error',
    })

    await expect(sendChatMessageStream({}, vi.fn()))
      .rejects.toThrow('Internal Server Error')
  })

  it('返回 HTML 错误页时提取简短信息', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: async () => '<!DOCTYPE html><html><body>Not Found</body></html>',
    })

    await expect(sendChatMessageStream({}, vi.fn()))
      .rejects.toThrow('服务器返回 404 错误，请确认后端已启动')
  })

  it('未收到任何数据时抛出空响应错误', async () => {
    const mockReader = {
      read: vi.fn().mockResolvedValue({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    await expect(sendChatMessageStream({}, vi.fn()))
      .rejects.toThrow('服务器返回了空响应，请确认后端正常运行')
  })

  it('处理跨 chunk 边界的 SSE 消息', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"te'),
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('xt":"split"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const onChunk = vi.fn()
    await sendChatMessageStream({}, onChunk)

    expect(onChunk).toHaveBeenCalledWith({ text: 'split' })
  })

  it('处理 buffer 中剩余的数据', async () => {
    const mockReader = {
      read: vi.fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"text":"first"}\n\ndata: {"text":"last"}'),
        })
        .mockResolvedValueOnce({ done: true }),
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      body: { getReader: () => mockReader },
    })

    const onChunk = vi.fn()
    await sendChatMessageStream({}, onChunk)

    expect(onChunk).toHaveBeenCalledTimes(2)
    expect(onChunk).toHaveBeenNthCalledWith(1, { text: 'first' })
    expect(onChunk).toHaveBeenNthCalledWith(2, { text: 'last' })
  })
})
