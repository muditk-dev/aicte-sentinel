import { apiRequest } from '../lib/api'
import { OCRJob, OCRExtractedField, OCRFieldVerifyRequest } from '../types'

export const ocrService = {
  async processDocumentOCR(documentId: string): Promise<OCRJob> {
    return apiRequest<OCRJob>(`/ocr/process/${documentId}`, {
      method: 'POST',
    })
  },

  async getDocumentOCR(documentId: string): Promise<OCRJob | null> {
    return apiRequest<OCRJob | null>(`/ocr/document/${documentId}`)
  },

  async listApplicationOCRFields(applicationId: string): Promise<OCRExtractedField[]> {
    return apiRequest<OCRExtractedField[]>(`/ocr/application/${applicationId}`)
  },

  async verifyField(fieldId: string, payload: OCRFieldVerifyRequest): Promise<OCRExtractedField> {
    return apiRequest<OCRExtractedField>(`/ocr/fields/${fieldId}/verify`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },
}
