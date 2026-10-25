import { apiRequest } from '../lib/api'
import { NotificationItem } from '../types'

export const notificationService = {
  async listNotifications(): Promise<NotificationItem[]> {
    return apiRequest<NotificationItem[]>('/notifications')
  },

  async markRead(notificationId: string): Promise<void> {
    return apiRequest(`/notifications/${notificationId}/read`, {
      method: 'POST',
    })
  },

  async markAllRead(): Promise<void> {
    return apiRequest('/notifications/read-all', {
      method: 'POST',
    })
  },
}
