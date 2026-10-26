const API_BASE = '/api/v1'

export interface ApiError {
  status: string
  code: string
  message: string
  details?: any
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('sentinel_token')
  const headers = new Headers(options.headers || {})

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`
  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    // Only redirect if not already on the login page
    if (!window.location.pathname.includes('/login')) {
      localStorage.removeItem('sentinel_token')
      localStorage.removeItem('sentinel_user')
      window.location.href = '/login'
    }
  }

  if (!response.ok) {
    let errorData: ApiError
    try {
      errorData = await response.json()
    } catch {
      errorData = {
        status: 'error',
        code: `HTTP_${response.status}`,
        message: response.statusText || 'Network request failed',
      }
    }
    throw errorData
  }

  // If 204 No Content
  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}
