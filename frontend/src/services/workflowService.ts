import { apiRequest } from '../lib/api'
import { WorkflowTemplate } from '../types'

export const workflowService = {
  async listTemplates(): Promise<WorkflowTemplate[]> {
    return apiRequest<WorkflowTemplate[]>('/workflows')
  },
}
