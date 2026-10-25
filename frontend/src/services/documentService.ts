import { apiRequest } from '../lib/api'
import { Document, DocumentVersion } from '../types'

export const documentService = {
  async listDocuments(applicationId: string): Promise<Document[]> {
    return apiRequest<Document[]>(`/applications/${applicationId}/documents`)
  },

  async getDocument(documentId: string): Promise<Document> {
    return apiRequest<Document>(`/documents/${documentId}`)
  },

  async listVersions(documentId: string): Promise<DocumentVersion[]> {
    return apiRequest<DocumentVersion[]>(`/documents/${documentId}/versions`)
  },

  async uploadDocument(
    applicationId: string,
    category: string,
    file: File
  ): Promise<Document> {
    const formData = new FormData()
    formData.append('category', category)
    formData.append('file', file)

    const token = localStorage.getItem('sentinel_token')
    const headers = new Headers()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await fetch(`/api/v1/applications/${applicationId}/documents`, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      let errData: any
      try {
        errData = await response.json()
      } catch {
        errData = { message: 'Upload request failed' }
      }
      throw errData
    }

    return response.json()
  },

  async downloadDocument(documentId: string, filename: string): Promise<void> {
    const token = localStorage.getItem('sentinel_token')
    const headers = new Headers()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }

    const response = await fetch(`/api/v1/documents/${documentId}/download`, {
      headers,
    })

    if (!response.ok) {
      let err: any
      try {
        err = await response.json()
      } catch {
        err = { message: 'Download failed' }
      }
      throw new Error(err.message || 'Cannot download document')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  },
}
