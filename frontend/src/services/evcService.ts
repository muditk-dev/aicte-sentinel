import { apiRequest } from '../lib/api'
import {
  Expert,
  ConflictCheckResult,
  EVCInspection,
  EVCPanelMember,
  EVCReportVersion,
} from '../types'

export const evcService = {
  // Experts
  async listExperts(filters?: { expert_type?: string; availability?: string; state?: string; district?: string }): Promise<Expert[]> {
    const params = new URLSearchParams()
    if (filters?.expert_type) params.append('expert_type', filters.expert_type)
    if (filters?.availability) params.append('availability', filters.availability)
    if (filters?.state) params.append('state', filters.state)
    if (filters?.district) params.append('district', filters.district)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return apiRequest<Expert[]>(`/experts${qs}`)
  },

  async createExpert(payload: any): Promise<Expert> {
    return apiRequest<Expert>('/experts', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getExpert(id: string): Promise<Expert> {
    return apiRequest<Expert>(`/experts/${id}`)
  },

  async checkExpertConflict(expertId: string, applicationId: string): Promise<ConflictCheckResult> {
    return apiRequest<ConflictCheckResult>(`/experts/${expertId}/conflict-check`, {
      method: 'POST',
      body: JSON.stringify({ expert_id: expertId, application_id: applicationId }),
    })
  },

  // Inspections
  async listInspections(filters?: { application_id?: string; status?: string; mode?: string }): Promise<EVCInspection[]> {
    const params = new URLSearchParams()
    if (filters?.application_id) params.append('application_id', filters.application_id)
    if (filters?.status) params.append('status', filters.status)
    if (filters?.mode) params.append('mode', filters.mode)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return apiRequest<EVCInspection[]>(`/inspections${qs}`)
  },

  async createInspection(payload: {
    application_id: string
    inspection_mode: string
    scheduled_start_date: string
    scheduled_end_date: string
    meeting_link?: string
    location_coordinates?: string
    location_address?: string
  }): Promise<EVCInspection> {
    return apiRequest<EVCInspection>('/inspections', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getInspection(id: string): Promise<EVCInspection> {
    return apiRequest<EVCInspection>(`/inspections/${id}`)
  },

  async assignExpert(
    inspectionId: string,
    payload: {
      expert_id: string
      role: string
      override_conflict?: boolean
      override_justification?: string
    }
  ): Promise<EVCPanelMember> {
    return apiRequest<EVCPanelMember>(`/inspections/${inspectionId}/experts`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async transitionInspection(inspectionId: string, targetStatus: string, remarks?: string): Promise<EVCInspection> {
    return apiRequest<EVCInspection>(`/inspections/${inspectionId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus, remarks }),
    })
  },

  async submitReport(inspectionId: string, payload: any): Promise<EVCReportVersion> {
    return apiRequest<EVCReportVersion>(`/inspections/${inspectionId}/reports`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listReportVersions(inspectionId: string): Promise<EVCReportVersion[]> {
    return apiRequest<EVCReportVersion[]>(`/inspections/${inspectionId}/reports`)
  },

  async reviewReport(
    inspectionId: string,
    versionId: string,
    payload: { review_status: string; review_remarks: string }
  ): Promise<EVCReportVersion> {
    return apiRequest<EVCReportVersion>(`/inspections/${inspectionId}/reports/${versionId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
