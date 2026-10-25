import { apiRequest } from '../lib/api'
import { DeficiencyNotice } from '../types'

export interface CreateDeficiencyItemPayload {
  requirement_title: string
  description: string
  required_corrective_action: string
  document_id?: string
}

export interface CreateDeficiencyNoticePayload {
  officer_remarks: string
  cure_days?: number
  items: CreateDeficiencyItemPayload[]
}

export interface SubmitResponsePayload {
  response_remarks: string
  attachment_document_ids?: string[]
}

export interface ReviewNoticePayload {
  action: 'RESOLVE' | 'REOPEN'
  officer_remarks: string
}

export const deficiencyService = {
  async listNotices(applicationId: string): Promise<DeficiencyNotice[]> {
    return apiRequest<DeficiencyNotice[]>(`/applications/${applicationId}/deficiencies`)
  },

  async getNotice(noticeId: string): Promise<DeficiencyNotice> {
    return apiRequest<DeficiencyNotice>(`/deficiencies/${noticeId}`)
  },

  async createNotice(
    applicationId: string,
    payload: CreateDeficiencyNoticePayload
  ): Promise<DeficiencyNotice> {
    return apiRequest<DeficiencyNotice>(`/applications/${applicationId}/deficiencies`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async submitResponse(
    noticeId: string,
    payload: SubmitResponsePayload
  ): Promise<DeficiencyNotice> {
    return apiRequest<DeficiencyNotice>(`/deficiencies/${noticeId}/respond`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async reviewNotice(
    noticeId: string,
    payload: ReviewNoticePayload
  ): Promise<DeficiencyNotice> {
    return apiRequest<DeficiencyNotice>(`/deficiencies/${noticeId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
