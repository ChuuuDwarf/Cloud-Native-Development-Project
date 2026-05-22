const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000'

function getMockUserId() {
  if (typeof window === 'undefined') return null

  return sessionStorage.getItem('mockUserId')
}

function getHeaders(): HeadersInit {
  const mockUserId = getMockUserId()

  return {
    'Content-Type': 'application/json',
    ...(mockUserId ? { 'x-user-id': mockUserId } : {}),
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const mockUserId = getMockUserId()

  const res = await fetch(`${API_BASE_URL}${path}`, {
    cache: 'no-store',
    headers: mockUserId ? { 'x-user-id': mockUserId } : undefined,
  })

  if (!res.ok) {
    throw new Error(`GET ${path} failed`)
  }

  return res.json()
}

export async function apiPost<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => null)
    throw new Error(error?.detail ?? `POST ${path} failed`)
  }

  return res.json()
}

export async function apiPatch<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    method: 'PATCH',
    headers: getHeaders(),
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => null)
    throw new Error(error?.detail ?? `PATCH ${path} failed`)
  }

  return res.json()
}