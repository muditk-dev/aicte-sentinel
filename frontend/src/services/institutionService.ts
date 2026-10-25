import { apiRequest } from '../lib/api'
import { Institution } from '../types'

export const institutionService = {
  async listInstitutions(region?: string, state?: string): Promise<Institution[]> {
    const query = new URLSearchParams()
    if (region) query.set('region', region)
    if (state) query.set('state', state)
    const qs = query.toString() ? `?${query.toString()}` : ''
    return apiRequest<Institution[]>(`/institutions${qs}`)
  },

  async getInstitution(id: string): Promise<Institution> {
    return apiRequest<Institution>(`/institutions/${id}`)
  },
}
