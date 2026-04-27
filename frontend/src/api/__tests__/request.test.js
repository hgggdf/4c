import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock axios.create so we can inspect the config
vi.mock('axios', () => {
  const mockInstance = {
    interceptors: {
      response: { use: vi.fn() },
    },
    post: vi.fn(),
  }
  return {
    default: {
      create: vi.fn(() => mockInstance),
    },
  }
})

describe('request.js — axios 实例配置', () => {
  let mockInstance

  beforeEach(async () => {
    vi.resetModules()
    // Re-import after reset so axios.create is called fresh
    const axiosMod = await import('axios')
    mockInstance = {
      interceptors: { response: { use: vi.fn() } },
      post: vi.fn(),
    }
    axiosMod.default.create.mockReturnValue(mockInstance)
    await import('../request.js')
  })

  it('baseURL 为空字符串（相对路径）', async () => {
    const axiosMod = await import('axios')
    const [config] = axiosMod.default.create.mock.calls.at(-1)
    expect(config.baseURL).toBe('')
  })

  it('timeout 为 120000ms', async () => {
    const axiosMod = await import('axios')
    const [config] = axiosMod.default.create.mock.calls.at(-1)
    expect(config.timeout).toBe(120000)
  })

  it('注册了 response 拦截器', () => {
    expect(mockInstance.interceptors.response.use).toHaveBeenCalledOnce()
  })
})

describe('request.js — response 拦截器', () => {
  let onFulfilled, onRejected

  beforeEach(async () => {
    vi.resetModules()
    const axiosMod = await import('axios')
    const inst = {
      interceptors: { response: { use: vi.fn() } },
    }
    axiosMod.default.create.mockReturnValue(inst)
    await import('../request.js')
    ;[onFulfilled, onRejected] = inst.interceptors.response.use.mock.calls[0]
  })

  it('成功时直接返回 response.data', () => {
    const result = onFulfilled({ data: { foo: 'bar' } })
    expect(result).toEqual({ foo: 'bar' })
  })

  it('超时错误（ECONNABORTED）返回中文提示', async () => {
    await expect(onRejected({ code: 'ECONNABORTED', message: 'timeout' }))
      .rejects.toThrow('请求超时，请检查网络连接')
  })

  it('超时错误（message 含 timeout）返回中文提示', async () => {
    await expect(onRejected({ message: 'timeout of 120000ms exceeded' }))
      .rejects.toThrow('请求超时，请检查网络连接')
  })

  it('无 response（网络断开）返回无法连接提示', async () => {
    await expect(onRejected({ message: 'Network Error' }))
      .rejects.toThrow('无法连接到服务器，请确认后端已启动')
  })

  it('服务器返回 detail 字段时使用 detail', async () => {
    await expect(
      onRejected({ response: { data: { detail: '参数错误' } }, message: 'Bad Request' })
    ).rejects.toThrow('参数错误')
  })

  it('服务器返回 message 字段时使用 message', async () => {
    await expect(
      onRejected({ response: { data: { message: '未授权' } }, message: 'Unauthorized' })
    ).rejects.toThrow('未授权')
  })

  it('无 detail/message 时回退到 error.message', async () => {
    await expect(
      onRejected({ response: { data: {} }, message: '500 Internal Server Error' })
    ).rejects.toThrow('500 Internal Server Error')
  })
})
