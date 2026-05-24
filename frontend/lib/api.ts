const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  'http://localhost:8000'
).replace(/\/api\/?$/, '')

type ApiErrorPayload = {
  detail?: unknown
  message?: unknown
  code?: string
  path?: string
  error?: {
    code?: string
    message?: unknown
    details?: unknown
  }
}

export class ApiError extends Error {
  status: number
  code?: string
  path?: string

  constructor(message: string, status: number, payload?: ApiErrorPayload) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = payload?.code
    this.path = payload?.path
  }
}

function getMockUserId() {
  if (typeof window === 'undefined') return null

  return sessionStorage.getItem('mockUserId')
}

function buildHeaders(hasBody: boolean): HeadersInit {
  const mockUserId = getMockUserId()

  return {
    ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
    ...(mockUserId ? { 'x-user-id': mockUserId } : {}),
  }
}

function stringifyDetail(detail: unknown, fallback: string): string {
  if (!detail) return fallback

  if (typeof detail === 'string') return detail

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item

        if (item && typeof item === 'object') {
          const record = item as Record<string, unknown>
          const msg = record.msg ?? record.message ?? record.detail
          const loc = Array.isArray(record.loc)
            ? record.loc.filter((part) => !['body', 'query', 'path'].includes(String(part))).join('.')
            : ''

          if (msg) return loc ? `${loc}: ${String(msg)}` : String(msg)
        }

        return ''
      })
      .filter(Boolean)

    return messages.length > 0 ? messages.join('；') : fallback
  }

  if (typeof detail === 'object') {
    const record = detail as Record<string, unknown>
    const message = record.message ?? record.detail
    return message ? String(message) : fallback
  }

  return String(detail)
}

async function readErrorPayload(res: Response): Promise<ApiErrorPayload | null> {
  const contentType = res.headers.get('content-type') ?? ''

  if (!contentType.includes('application/json')) {
    return null
  }

  return res.json().catch(() => null)
}

async function parseResponse<T>(res: Response, fallbackMessage: string): Promise<T> {
  if (!res.ok) {
    const payload = await readErrorPayload(res)
    const message = stringifyDetail(payload?.detail ?? payload?.message ?? payload?.error?.message, fallbackMessage)
    throw new ApiError(message, res.status, payload ?? undefined)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return res.json() as Promise<T>
}

async function apiRequest<T>(
  method: 'GET' | 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body?: unknown,
): Promise<T> {
  const hasBody = body !== undefined
  const fallbackMessage = `${method} ${path} failed`

  let res: Response

  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method,
      cache: method === 'GET' ? 'no-store' : undefined,
      credentials: 'include',
      headers: buildHeaders(hasBody),
      body: hasBody ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new Error('無法連線到後端服務，請確認 API 伺服器是否已啟動')
  }

  return parseResponse<T>(res, fallbackMessage)
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>('GET', path)
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>('POST', path, body)
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiRequest<T>('PATCH', path, body)
}

export function apiDelete<T>(path: string): Promise<T> {
  return apiRequest<T>('DELETE', path)
}
