import { apiRequest } from '../lib/api'
import { StatutoryDecision } from '../types'

export interface IssueDecisionPayload {
  application_id: string
  decision_type: string
  reasons: string
  evidence_references: string[]
  intake_approved?: number
  valid_for_years: number
  governing_policy_version?: string
  conditions: Array<{
    condition_code: string
    description: string
    due_date: string
  }>
  declaration_attestation: string
}

export const decisionService = {
  async listDecisions(): Promise<StatutoryDecision[]> {
    return apiRequest<StatutoryDecision[]>('/decisions')
  },

  async getDecisionByApplication(applicationId: string): Promise<StatutoryDecision | null> {
    return apiRequest<StatutoryDecision | null>(`/decisions/application/${applicationId}`)
  },

  async issueDecision(payload: IssueDecisionPayload): Promise<StatutoryDecision> {
    return apiRequest<StatutoryDecision>('/decisions', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async requestReconsideration(
    decisionId: string,
    payload: { appeal_reason: string; appeal_petition_reference: string }
  ): Promise<StatutoryDecision> {
    return apiRequest<StatutoryDecision>(`/decisions/${decisionId}/reconsider`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
