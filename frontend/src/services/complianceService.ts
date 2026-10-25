import { apiRequest } from '../lib/api'
import {
  ComplianceObligation,
  ComplianceSummaryReport,
  InstitutionComplianceReportItem,
  ComplianceDeadlineItem,
  ComplianceDeficiencyReportItem,
  ComplianceEscalation,
  EvidenceSubmitPayload,
  OfficerReviewPayload,
  ObligationCreatePayload,
} from '../types'

export interface ListObligationsParams {
  category?: string
  status?: string
  institution_id?: string
  search?: string
  overdue_only?: boolean
  limit?: number
  offset?: number
}

export const complianceService = {
  async listObligations(params: ListObligationsParams = {}): Promise<ComplianceObligation[]> {
    const query = new URLSearchParams()
    if (params.category) query.append('category', params.category)
    if (params.status) query.append('status', params.status)
    if (params.institution_id) query.append('institution_id', params.institution_id)
    if (params.search) query.append('search', params.search)
    if (params.overdue_only) query.append('overdue_only', 'true')
    if (params.limit) query.append('limit', params.limit.toString())
    if (params.offset) query.append('offset', params.offset.toString())

    const qs = query.toString()
    return apiRequest<ComplianceObligation[]>(`/compliance/obligations${qs ? `?${qs}` : ''}`)
  },

  async getObligation(id: string): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>(`/compliance/obligations/${id}`)
  },

  async createObligation(payload: ObligationCreatePayload): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>('/compliance/obligations', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateObligation(id: string, payload: Partial<ObligationCreatePayload>): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>(`/compliance/obligations/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  async submitEvidence(id: string, payload: EvidenceSubmitPayload): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>(`/compliance/obligations/${id}/evidence`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async officerReview(id: string, payload: OfficerReviewPayload): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>(`/compliance/obligations/${id}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async transitionStatus(id: string, target_status: string, comments?: string): Promise<ComplianceObligation> {
    return apiRequest<ComplianceObligation>(`/compliance/obligations/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify({ target_status, comments }),
    })
  },

  async getSummaryReport(): Promise<ComplianceSummaryReport> {
    return apiRequest<ComplianceSummaryReport>('/compliance/reports/summary')
  },

  async getInstitutionReports(region?: string): Promise<InstitutionComplianceReportItem[]> {
    const qs = region ? `?region=${encodeURIComponent(region)}` : ''
    return apiRequest<InstitutionComplianceReportItem[]>(`/compliance/reports/by-institution${qs}`)
  },

  async getDeadlinesReport(daysAhead = 60): Promise<ComplianceDeadlineItem[]> {
    return apiRequest<ComplianceDeadlineItem[]>(`/compliance/reports/deadlines?days_ahead=${daysAhead}`)
  },

  async getDeficienciesReport(): Promise<ComplianceDeficiencyReportItem[]> {
    return apiRequest<ComplianceDeficiencyReportItem[]>('/compliance/reports/deficiencies')
  },

  async listEscalations(unresolvedOnly = false): Promise<ComplianceEscalation[]> {
    return apiRequest<ComplianceEscalation[]>(`/compliance/escalations?unresolved_only=${unresolvedOnly}`)
  },

  async triggerMonitoringWorker(): Promise<{ status: string; actions_evaluated: number; message: string; timestamp?: string }> {
    return apiRequest<{ status: string; actions_evaluated: number; message: string; timestamp?: string }>('/compliance/monitoring/trigger', {
      method: 'POST',
    })
  },

  getExportCSVUrl(category?: string, status?: string): string {
    const query = new URLSearchParams()
    if (category) query.append('category', category)
    if (status) query.append('status', status)
    const qs = query.toString()
    return `/api/v1/compliance/reports/export-csv${qs ? `?${qs}` : ''}`
  },
}
