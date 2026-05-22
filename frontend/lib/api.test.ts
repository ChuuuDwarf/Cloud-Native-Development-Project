import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, apiDelete, apiGet, apiPatch, apiPost } from './api'

function jsonResponse(body: unknown, init?: ResponseInit) {
  return new Response(JSON.stringify(body), {
    status: init?.status ?? 200,
    headers: {
      'content-type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
}

describe('api helpers', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('apiGet 會送 GET request，並帶入 mock user header', async () => {
    sessionStorage.setItem('mockUserId', 'user-laba-001')

    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(jsonResponse({ ok: true }))

    const result = await apiGet<{ ok: boolean }>('/api/samples')

    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/samples', {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'x-user-id': 'user-laba-001',
      },
      body: undefined,
    })
  })

  it('apiPost 會送 JSON body 和 Content-Type', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(jsonResponse({ id: 1 }))

    const result = await apiPost<{ id: number }>('/api/wips', {
      name: 'test',
    })

    expect(result).toEqual({ id: 1 })
    expect(fetchMock).toHaveBeenCalledWith('http://127.0.0.1:8000/api/wips', {
      method: 'POST',
      cache: undefined,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ name: 'test' }),
    })
  })

  it('apiPatch 會送 PATCH request', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: 'updated' }))

    const result = await apiPatch<{ status: string }>('/api/samples/1', {
      note: '更新',
    })

    expect(result.status).toBe('updated')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/samples/1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ note: '更新' }),
      }),
    )
  })

  it('apiDelete 遇到 204 會回傳 undefined', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }))

    const result = await apiDelete<void>('/api/samples/1')

    expect(result).toBeUndefined()
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/api/samples/1',
      expect.objectContaining({
        method: 'DELETE',
      }),
    )
  })

  it('後端回傳 detail string 時會丟出 ApiError', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: 'Sample not found',
          code: 'NOT_FOUND',
          path: '/api/samples/1',
        },
        { status: 404 },
      ),
    )

    await expect(apiGet('/api/samples/1')).rejects.toMatchObject({
      name: 'ApiError',
      message: 'Sample not found',
      status: 404,
      code: 'NOT_FOUND',
      path: '/api/samples/1',
    })
  })

  it('後端回傳 validation detail array 時會整理成可讀訊息', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: [
            {
              loc: ['body', 'wips', 0, 'lab_name'],
              msg: 'Field required',
            },
            {
              loc: ['body', 'action'],
              message: 'Invalid action',
            },
          ],
        },
        { status: 422 },
      ),
    )

    await expect(apiPost('/api/samples/1/actions', {})).rejects.toThrow(
      'wips.0.lab_name: Field required；action: Invalid action',
    )
  })

  it('後端回傳 detail object 時會解析 message/detail', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(
      jsonResponse(
        {
          detail: {
            message: '物件錯誤訊息',
          },
        },
        { status: 400 },
      ),
    )

    await expect(apiPost('/api/test', {})).rejects.toThrow('物件錯誤訊息')
  })

  it('非 JSON 錯誤回應會使用 fallback message', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockResolvedValueOnce(
      new Response('server error', {
        status: 500,
        headers: {
          'content-type': 'text/plain',
        },
      }),
    )

    await expect(apiGet('/api/broken')).rejects.toThrow('GET /api/broken failed')
  })

  it('fetch 失敗時會顯示無法連線到後端服務', async () => {
    const fetchMock = vi.mocked(fetch)
    fetchMock.mockRejectedValueOnce(new Error('network failed'))

    await expect(apiGet('/api/samples')).rejects.toThrow(
      '無法連線到後端服務，請確認 API 伺服器是否已啟動',
    )
  })

  it('ApiError 會保留 status/code/path', () => {
    const error = new ApiError('錯誤', 400, {
      code: 'BAD_REQUEST',
      path: '/api/test',
    })

    expect(error.name).toBe('ApiError')
    expect(error.message).toBe('錯誤')
    expect(error.status).toBe(400)
    expect(error.code).toBe('BAD_REQUEST')
    expect(error.path).toBe('/api/test')
  })
})