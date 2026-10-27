import { apiRequest } from '../lib/api'
import { AuthResponse, UserProfile } from '../types'

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    localStorage.setItem('sentinel_token', res.access_token)
    localStorage.setItem('sentinel_user', JSON.stringify(res.user))
    return res
  },

  async checkBootstrapStatus(): Promise<{ bootstrap_available: boolean; total_users: number; message: string }> {
    return apiRequest<{ bootstrap_available: boolean; total_users: number; message: string }>('/auth/bootstrap/status')
  },

  async bootstrapAdmin(data: { email: string; password: string; full_name: string; designation?: string }): Promise<AuthResponse> {
    const res = await apiRequest<AuthResponse>('/auth/bootstrap', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    localStorage.setItem('sentinel_token', res.access_token)
    localStorage.setItem('sentinel_user', JSON.stringify(res.user))
    return res
  },

  async getMe(): Promise<UserProfile> {
    const user = await apiRequest<UserProfile>('/auth/me')
    localStorage.setItem('sentinel_user', JSON.stringify(user))
    return user
  },

  logout(): void {
    localStorage.removeItem('sentinel_token')
    localStorage.removeItem('sentinel_user')
    window.location.href = '/login'
  },

  getCurrentUser(): UserProfile | null {
    const raw = localStorage.getItem('sentinel_user')
    if (!raw) return null
    try {
      return JSON.parse(raw) as UserProfile
    } catch {
      return null
    }
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('sentinel_token')
  },
}
