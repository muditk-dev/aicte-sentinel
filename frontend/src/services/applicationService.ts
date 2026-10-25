import { apiRequest } from '../lib/api'
import { Application } from '../types'

export interface CreateApplicationPayload {
  template_id: string
  academic_year?: string
  submission_data?: Record<string, any>
}

export interface TransitionPayload {
  target_status: string
  remarks: string
  checklist_verification?: Record<string, any>
}

export const applicationService = {
  async listApplications(status?: string): Promise<Application[]> {
    const params = status ? `?status=${encodeURIComponent(status)}` : ''
    return apiRequest<Application[]>(`/applications${params}`)
  },

  async getApplication(id: string): Promise<Application> {
    return apiRequest<Application>(`/applications/${id}`)
  },

  async createApplication(payload: CreateApplicationPayload): Promise<Application> {
    return apiRequest<Application>('/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async transitionState(id: string, payload: TransitionPayload): Promise<Application> {
    return apiRequest<Application>(`/applications/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
