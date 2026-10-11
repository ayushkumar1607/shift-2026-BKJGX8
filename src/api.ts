const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.name = 'ApiError'; this.status = status }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      credentials: 'include',
      headers: { ...(init.body ? { 'Content-Type': 'application/json' } : {}), ...init.headers },
    })
  } catch {
    throw new ApiError('The EV Shield service is not responding. Start the backend and try again.', 0)
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    let message = body.detail ?? body.message ?? 'Something went wrong. Please try again.'
    if (Array.isArray(message)) message = message.map((item: { msg?: string }) => item.msg).join(' ')
    throw new ApiError(String(message), response.status)
  }
  return body as T
}

export const authApi = {
  me: () => api<import('./types').User>('/api/auth/me'),
  login: (identifier: string, password: string) => api<{ user: import('./types').User; message: string }>('/api/auth/login', { method: 'POST', body: JSON.stringify({ identifier, password }) }),
  signup: (data: { full_name: string; email?: string; phone?: string; password: string; confirm_password: string; terms_accepted: boolean }) => api<{ user: import('./types').User; message: string }>('/api/auth/signup', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => api<{ message: string }>('/api/auth/logout', { method: 'POST' }),
}

