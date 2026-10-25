import { apiRequest } from '../lib/api'
import { AuditEvent, AuditVerification } from '../types'

export const auditService = {
  async listEvents(limit: number = 50): Promise<AuditEvent[]> {
    return apiRequest<AuditEvent[]>(`/audit/events?limit=${limit}`)
  },

  async verifyLedger(): Promise<AuditVerification> {
    return apiRequest<AuditVerification>('/audit/verify')
  },
}
