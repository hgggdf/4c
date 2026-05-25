import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../request.js', () => ({
  default: {
    get: vi.fn(),
  },
}))

describe('stock.js change_pct normalization', () => {
  let request
  let getQuote

  beforeEach(async () => {
    vi.resetModules()
    request = (await import('../request.js')).default
    request.get.mockReset()
    ;({ getQuote } = await import('../stock.js'))
  })

  it('converts decimal change_pct to display percent for quotes', async () => {
    request.get.mockResolvedValue({
      name: 'Test Stock',
      quote: {
        symbol: '000538',
        name: 'Test Stock',
        price: 52.62,
        change_pct: 0.038,
      },
    })

    const quote = await getQuote('000538')

    expect(quote.change_pct).toBeCloseTo(3.8)
    expect(quote.change_percent).toBeCloseTo(3.8)
  })
})
