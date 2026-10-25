import { apiRequest } from '../lib/api'
import { DelayRiskPrediction, ModelVersion, RiskOverviewItem } from '../types'

export const intelligenceService = {
  async getApplicationDelayRisk(applicationId: string): Promise<DelayRiskPrediction> {
    return apiRequest<DelayRiskPrediction>(`/intelligence/risk/${applicationId}`)
  },

  async recomputeApplicationDelayRisk(applicationId: string): Promise<DelayRiskPrediction> {
    return apiRequest<DelayRiskPrediction>(`/intelligence/risk/${applicationId}/recompute`, {
      method: 'POST',
    })
  },

  async getRiskOverview(params?: { region?: string; status?: string }): Promise<RiskOverviewItem[]> {
    const query = new URLSearchParams()
    if (params?.region) query.append('region', params.region)
    if (params?.status) query.append('status', params.status)
    const qs = query.toString() ? `?${query.toString()}` : ''
    return apiRequest<RiskOverviewItem[]>(`/intelligence/overview${qs}`)
  },

  async listModelVersions(): Promise<ModelVersion[]> {
    return apiRequest<ModelVersion[]>('/intelligence/models')
  },
}
