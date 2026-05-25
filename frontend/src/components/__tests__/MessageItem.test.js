import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageItem from '../MessageItem.vue'

describe('MessageItem quote display', () => {
  it('converts decimal change_pct to display percent', () => {
    const wrapper = mount(MessageItem, {
      props: {
        message: {
          role: 'user',
          content: 'quote',
          createdAt: Date.now(),
          extra: {
            symbol: '000538',
            name: 'Test Stock',
            price: 52.62,
            change: 2,
            change_pct: 0.038,
          },
        },
      },
    })

    expect(wrapper.text()).toContain('+3.80%')
  })
})
