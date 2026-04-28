import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatBox from '../ChatBox.vue'
import * as chatApi from '../../api/chat'

vi.mock('../../api/chat', () => ({
  uploadPDF: vi.fn(),
}))

// @vue/test-utils trigger() 不会把额外属性合并到原生 Event 上，
// dataTransfer 需要通过直接调用 onDrop 来模拟。
function simulateDrop(wrapper, item) {
  wrapper.vm.onDrop({
    dataTransfer: { getData: () => JSON.stringify(item) },
    preventDefault: vi.fn(),
  })
  return wrapper.vm.$nextTick()
}

describe('ChatBox.vue — 用户提交触发链路', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(ChatBox, {
      props: { loading: false },
    })
  })

  it('用户输入文本后点击发送按钮，emit submit 事件', async () => {
    const textarea = wrapper.find('textarea')
    await textarea.setValue('分析恒瑞医药')

    const sendBtn = wrapper.find('.send-btn')
    await sendBtn.trigger('click')

    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toEqual({
      message: '分析恒瑞医药',
      targets: [],
    })
  })

  it('用户按 Enter 键提交，emit submit 事件', async () => {
    const textarea = wrapper.find('textarea')
    await textarea.setValue('查看行业趋势')
    await textarea.trigger('keydown.enter', { key: 'Enter' })

    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toEqual({
      message: '查看行业趋势',
      targets: [],
    })
  })

  it('提交后清空输入框', async () => {
    const textarea = wrapper.find('textarea')
    await textarea.setValue('测试消息')
    await wrapper.find('.send-btn').trigger('click')

    expect(textarea.element.value).toBe('')
  })

  it('拖入标的后提交，payload 包含 targets', async () => {
    await simulateDrop(wrapper, { symbol: '600276', name: '恒瑞医药', type: 'stock' })

    const textarea = wrapper.find('textarea')
    await textarea.setValue('分析这只股票')
    await wrapper.find('.send-btn').trigger('click')

    expect(wrapper.emitted('submit')[0][0]).toEqual({
      message: '分析这只股票',
      targets: [{ symbol: '600276', name: '恒瑞医药', type: 'stock' }],
    })
  })

  it('拖入多个标的，payload 包含所有 targets', async () => {
    await simulateDrop(wrapper, { symbol: '600276', name: '恒瑞医药', type: 'stock' })
    await simulateDrop(wrapper, { symbol: '000661', name: '长春高新', type: 'stock' })

    await wrapper.find('textarea').setValue('对比分析')
    await wrapper.find('.send-btn').trigger('click')

    expect(wrapper.emitted('submit')[0][0].targets).toHaveLength(2)
    expect(wrapper.emitted('submit')[0][0].targets).toEqual([
      { symbol: '600276', name: '恒瑞医药', type: 'stock' },
      { symbol: '000661', name: '长春高新', type: 'stock' },
    ])
  })

  it('提交后清空 droppedItems', async () => {
    await simulateDrop(wrapper, { symbol: '600276', name: '恒瑞医药', type: 'stock' })

    await wrapper.find('textarea').setValue('分析')
    await wrapper.find('.send-btn').trigger('click')

    expect(wrapper.vm.droppedItems).toEqual([])
  })

  it('只拖入标的不输入文本也可提交', async () => {
    await simulateDrop(wrapper, { symbol: '600276', name: '恒瑞医药', type: 'stock' })

    await wrapper.find('.send-btn').trigger('click')

    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toEqual({
      message: '',
      targets: [{ symbol: '600276', name: '恒瑞医药', type: 'stock' }],
    })
  })

  it('空文本且无标的时不提交', async () => {
    await wrapper.find('.send-btn').trigger('click')
    expect(wrapper.emitted('submit')).toBeFalsy()
  })

  it('loading 时禁用发送按钮', async () => {
    await wrapper.setProps({ loading: true })
    const sendBtn = wrapper.find('.send-btn')
    expect(sendBtn.attributes('disabled')).toBeDefined()
  })

  it('拖入重复标的时不重复添加', async () => {
    const item = { symbol: '600276', name: '恒瑞医药', type: 'stock' }

    await simulateDrop(wrapper, item)
    await simulateDrop(wrapper, item)

    expect(wrapper.vm.droppedItems).toHaveLength(1)
  })

  it('点击标签的 × 可移除标的', async () => {
    await simulateDrop(wrapper, { symbol: '600276', name: '恒瑞医药', type: 'stock' })

    const removeBtn = wrapper.find('.rm')
    await removeBtn.trigger('click')

    expect(wrapper.vm.droppedItems).toEqual([])
  })
})

describe('ChatBox.vue — PDF 上传', () => {
  let wrapper

  beforeEach(() => {
    wrapper = mount(ChatBox, {
      props: { loading: false },
    })
    vi.clearAllMocks()
  })

  it('选择文件后调用 uploadPDF', async () => {
    chatApi.uploadPDF.mockResolvedValue({ success: true })

    const file = new File(['content'], 'report.pdf', { type: 'application/pdf' })
    const input = wrapper.find('input[type="file"]')

    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')

    expect(chatApi.uploadPDF).toHaveBeenCalledWith(file, expect.any(Function))
  })

  it('上传过程中显示进度', async () => {
    let progressCallback
    chatApi.uploadPDF.mockImplementation((file, onProgress) => {
      progressCallback = onProgress
      return new Promise(resolve => {
        setTimeout(() => {
          progressCallback(50)
          progressCallback(100)
          resolve({ success: true })
        }, 10)
      })
    })

    const file = new File(['content'], 'report.pdf', { type: 'application/pdf' })
    const input = wrapper.find('input[type="file"]')

    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.uploadState.active).toBe(true)
    expect(wrapper.vm.uploadState.fileName).toBe('report.pdf')

    await new Promise(resolve => setTimeout(resolve, 20))
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.uploadState.percent).toBe(100)
    expect(wrapper.vm.uploadState.done).toBe(true)
  })

  it('上传失败时显示错误', async () => {
    chatApi.uploadPDF.mockRejectedValue(new Error('网络错误'))
    window.alert = vi.fn()

    const file = new File(['content'], 'report.pdf', { type: 'application/pdf' })
    const input = wrapper.find('input[type="file"]')

    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })

    await input.trigger('change')
    await wrapper.vm.$nextTick()

    expect(window.alert).toHaveBeenCalledWith('上传失败：网络错误')
    expect(wrapper.vm.uploadState.active).toBe(false)
  })
})
