import { apiRequest } from '../lib/api'
import { ScrutinyFinding } from '../types'

export interface RecordFindingPayload {
  category: string
  document_id?: string
  finding_status: string
  reason: string
  notes?: string
}

export const scrutinyService = {
  async listFindings(applicationId: string): Promise<ScrutinyFinding[]> {
    return apiRequest<ScrutinyFinding[]>(`/applications/${applicationId}/scrutiny`)
  },

  async recordFinding(
    applicationId: string,
    payload: RecordFindingPayload
  ): Promise<ScrutinyFinding> {
    return apiRequest<ScrutinyFinding>(`/applications/${applicationId}/scrutiny`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
