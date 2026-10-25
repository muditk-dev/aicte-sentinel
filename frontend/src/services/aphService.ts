import { apiRequest } from '../lib/api'
import { APHQueryRequest, APHQueryResponse, APHSourceDocument, APHClause } from '../types'

export const aphService = {
  async askAssistant(payload: APHQueryRequest): Promise<APHQueryResponse> {
    return apiRequest<APHQueryResponse>('/aph/ask', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async listSources(): Promise<APHSourceDocument[]> {
    return apiRequest<APHSourceDocument[]>('/aph/sources')
  },

  async listClauses(category?: string): Promise<APHClause[]> {
    const qs = category ? `?category=${category}` : ''
    return apiRequest<APHClause[]>(`/aph/clauses${qs}`)
  },

  async getHistory(): Promise<APHQueryResponse[]> {
    return apiRequest<APHQueryResponse[]>('/aph/history')
  },

  async submitFeedback(queryId: string, rating: number): Promise<APHQueryResponse> {
    return apiRequest<APHQueryResponse>(`/aph/feedback/${queryId}`, {
      method: 'POST',
      body: JSON.stringify({ rating }),
    })
  },
}
