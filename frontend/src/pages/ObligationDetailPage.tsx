import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import {
  FileText,
  Building,
  CheckCircle2,
  AlertTriangle,
  Upload,
  ArrowLeft,
  RefreshCw,
  Clock,
  ShieldCheck,
  UserCheck,
  FileCheck,
  XCircle,
} from 'lucide-react'

export const ObligationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()

  const isOfficerOrAdmin = user?.roles.some((r) =>
    ['SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER'].includes(r.code)
  )

  // Submit Evidence Modal State
  const [isEvidenceModalOpen, setIsEvidenceModalOpen] = useState(false)
  const [evidenceTitle, setEvidenceTitle] = useState('')
  const [evidenceDesc, setEvidenceDesc] = useState('')
  const [submissionNotes, setSubmissionNotes] = useState('')
  const [fileUrl, setFileUrl] = useState('')
  const [evidenceError, setEvidenceError] = useState<string | null>(null)

  // Officer Review Modal State
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
  const [reviewDecision, setReviewDecision] = useState<'VERIFIED_COMPLIANT' | 'DEFICIENCY_FLAGGED' | 'CLOSED'>('VERIFIED_COMPLIANT')
  const [reviewComments, setReviewComments] = useState('')
  const [deficiencyCureDays, setDeficiencyCureDays] = useState<number>(14)
  const [reviewError, setReviewError] = useState<string | null>(null)

  // Fetch Obligation
  const { data: obligation, isLoading, isError, refetch } = useQuery({
    queryKey: ['compliance-obligation-detail', id],
    queryFn: () => complianceService.getObligation(id!),
    enabled: Boolean(id),
  })

  // Submit Evidence Mutation
  const evidenceMutation = useMutation({
    mutationFn: (payload: any) => complianceService.submitEvidence(id!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-obligation-detail', id] })
      queryClient.invalidateQueries({ queryKey: ['compliance-obligations'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-summary'] })
      setIsEvidenceModalOpen(false)
      setEvidenceTitle('')
      setEvidenceDesc('')
      setSubmissionNotes('')
      setFileUrl('')
      setEvidenceError(null)
    },
    onError: (err: any) => {
      setEvidenceError(err.message || 'Failed to upload compliance evidence')
    },
  })

  // Officer Review Mutation
  const reviewMutation = useMutation({
    mutationFn: (payload: any) => complianceService.officerReview(id!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-obligation-detail', id] })
      queryClient.invalidateQueries({ queryKey: ['compliance-obligations'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-summary'] })
      setIsReviewModalOpen(false)
      setReviewComments('')
      setReviewError(null)
    },
    onError: (err: any) => {
      setReviewError(err.message || 'Failed to submit officer review determination')
    },
  })

  const handleEvidenceSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!evidenceTitle) {
      setEvidenceError('Evidence title is required.')
      return
    }

    evidenceMutation.mutate({
      title: evidenceTitle,
      description: evidenceDesc || undefined,
      submission_notes: submissionNotes || undefined,
      file_url: fileUrl || `/vault/compliance/${Date.now()}_evidence.pdf`,
      sha256_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    })
  }

  const handleReviewSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!reviewComments) {
      setReviewError('Review comments are mandatory for statutory audit accountability.')
      return
    }

    reviewMutation.mutate({
      decision: reviewDecision,
      review_comments: reviewComments,
      deficiency_cure_days: reviewDecision === 'DEFICIENCY_FLAGGED' ? deficiencyCureDays : undefined,
    })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 space-y-3">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-sm text-slate-500">Loading statutory obligation docket...</p>
      </div>
    )
  }

  if (isError || !obligation) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
        <AlertTriangle className="w-8 h-8 text-red-600 mx-auto mb-2" />
        <h3 className="text-sm font-bold text-red-900">Obligation Docket Not Found</h3>
        <p className="text-xs text-red-700 mt-1">
          The requested compliance obligation does not exist or you lack permission to inspect it.
        </p>
        <Link
          to="/compliance/obligations"
          className="mt-3 inline-block px-3 py-1.5 text-xs font-semibold text-white bg-blue-700 rounded"
        >
          Return to Obligations Register
        </Link>
      </div>
    )
  }

  const isPastDue = new Date(obligation.due_date) < new Date() && obligation.status !== 'COMPLIANT' && obligation.status !== 'CLOSED'

  return (
    <div className="space-y-6">
      {/* Back button & Breadcrumb */}
      <div className="flex items-center space-x-2 text-xs text-slate-500">
        <Link to="/compliance/obligations" className="inline-flex items-center text-blue-700 hover:underline">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Register
        </Link>
        <span>/</span>
        <span className="font-mono font-semibold text-slate-700">{obligation.obligation_code}</span>
      </div>

      {/* Main Header Card */}
      <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2 mb-1">
            <span className="font-mono text-xs font-bold text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              {obligation.obligation_code}
            </span>
            <StatusBadge status={obligation.status} />
            {obligation.is_synthetic_demonstration && (
              <span className="text-[10px] px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-semibold">
                SYNTHETIC DEMO
              </span>
            )}
          </div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">{obligation.title}</h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center space-x-3">
            <span className="flex items-center">
              <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
              {obligation.institution_name || 'Assigned Institution'}
            </span>
            <span>•</span>
            <span className="font-mono text-slate-600">Statutory Norm: {obligation.source_reference}</span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {obligation.status !== 'CLOSED' && (
            <button
              onClick={() => setIsEvidenceModalOpen(true)}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-blue-700 rounded hover:bg-blue-800 shadow-sm transition-colors"
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" />
              Submit Evidence
            </button>
          )}

          {isOfficerOrAdmin && obligation.status !== 'CLOSED' && (
            <button
              onClick={() => setIsReviewModalOpen(true)}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-slate-800 bg-amber-50 border border-amber-300 rounded hover:bg-amber-100 shadow-sm transition-colors"
            >
              <UserCheck className="w-3.5 h-3.5 mr-1.5 text-amber-700" />
              Officer Review
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded shadow-sm"
            title="Refresh docket"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Grid: Details & Evidence */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Obligation Specification */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-slate-900 tracking-tight border-b border-slate-100 pb-2">
              Statutory Specification & Norm Description
            </h2>
            <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-wrap">{obligation.description}</p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-3 border-t border-slate-100 text-xs">
              <div>
                <span className="text-slate-400 block text-[10px] font-semibold uppercase">Category</span>
                <span className="font-semibold text-slate-800">{obligation.category.replace('_', ' ')}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] font-semibold uppercase">Recurrence</span>
                <span className="font-semibold text-slate-800">{obligation.recurrence}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] font-semibold uppercase">Issue Date</span>
                <span className="font-mono text-slate-800">{formatDate(obligation.issue_date)}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] font-semibold uppercase">Statutory Deadline</span>
                <span className={`font-mono font-semibold ${isPastDue ? 'text-red-700' : 'text-slate-800'}`}>
                  {formatDate(obligation.due_date)}
                </span>
              </div>
            </div>
          </div>

          {/* Submitted Supporting Evidence */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h2 className="text-sm font-bold text-slate-900 tracking-tight flex items-center">
                <FileCheck className="w-4 h-4 mr-1.5 text-blue-700" />
                Submitted Supporting Evidence ({obligation.evidences?.length || 0})
              </h2>

              {obligation.status !== 'CLOSED' && (
                <button
                  onClick={() => setIsEvidenceModalOpen(true)}
                  className="text-xs text-blue-700 hover:underline font-semibold"
                >
                  + Add Evidence
                </button>
              )}
            </div>

            {!obligation.evidences || obligation.evidences.length === 0 ? (
              <div className="p-8 text-center text-slate-400">
                <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-xs">No compliance evidence has been submitted yet.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {obligation.evidences.map((ev) => (
                  <div key={ev.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-xs space-y-1.5">
                    <div className="flex items-start justify-between">
                      <span className="font-bold text-slate-900">{ev.title}</span>
                      <span className="text-[10px] font-mono text-slate-400">{formatDate(ev.created_at)}</span>
                    </div>
                    {ev.description && <p className="text-slate-600 leading-relaxed">{ev.description}</p>}
                    {ev.submission_notes && (
                      <p className="text-slate-500 italic text-[11px]">Note: "{ev.submission_notes}"</p>
                    )}
                    {ev.sha256_hash && (
                      <div className="pt-1.5 flex items-center text-[10px] text-slate-500 font-mono">
                        <ShieldCheck className="w-3 h-3 mr-1 text-emerald-600" />
                        <span className="truncate max-w-sm">SHA-256: {ev.sha256_hash}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Review Status & History Timeline */}
        <div className="space-y-6">
          {/* Review Officer Card */}
          <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Reviewing Officer Assignment</h3>
            <div className="flex items-center space-x-2 text-xs">
              <div className="p-2 rounded-full bg-blue-100 text-blue-700">
                <UserCheck className="w-4 h-4" />
              </div>
              <div>
                <span className="font-bold text-slate-900 block">{obligation.assigned_officer_name || 'Unassigned Scrutiny Desk'}</span>
                <span className="text-[11px] text-slate-500">Regional Scrutiny Officer</span>
              </div>
            </div>
            {isOfficerOrAdmin && obligation.status !== 'CLOSED' && (
              <button
                onClick={() => setIsReviewModalOpen(true)}
                className="w-full mt-2 py-1.5 text-xs font-semibold text-center text-white bg-blue-700 hover:bg-blue-800 rounded transition-colors"
              >
                Conduct Review Determination
              </button>
            )}
          </div>

          {/* Review History Audit Timeline */}
          <div className="bg-white p-5 rounded-lg border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-500" />
              Status & Review Audit Trail
            </h3>

            {!obligation.history || obligation.history.length === 0 ? (
              <p className="text-xs text-slate-400">No review events logged.</p>
            ) : (
              <div className="relative pl-4 space-y-4 border-l border-slate-200 text-xs">
                {obligation.history.map((h) => (
                  <div key={h.id} className="relative">
                    <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                    <div className="font-semibold text-slate-800 flex items-center justify-between">
                      <span>{h.action.replace('_', ' ')}</span>
                      <span className="text-[10px] font-mono text-slate-400">{formatDate(h.created_at)}</span>
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">
                      <span className="font-semibold">{h.previous_status}</span> ➔ <span className="font-semibold text-blue-700">{h.new_status}</span>
                    </div>
                    {h.comments && <p className="text-slate-600 mt-1 bg-slate-50 p-2 rounded text-[11px]">{h.comments}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Submit Evidence Modal */}
      {isEvidenceModalOpen && (
        <Modal
          isOpen={isEvidenceModalOpen}
          onClose={() => setIsEvidenceModalOpen(false)}
          title="Submit Supporting Compliance Evidence"
        >
          <form onSubmit={handleEvidenceSubmit} className="space-y-4 text-xs">
            {evidenceError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-700 rounded text-xs flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 flex-shrink-0" />
                {evidenceError}
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-bold mb-1">Evidence Title *</label>
              <input
                type="text"
                value={evidenceTitle}
                onChange={(e) => setEvidenceTitle(e.target.value)}
                placeholder="e.g. Audited Faculty Muster Roll AY 2026-27"
                required
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">Description</label>
              <textarea
                value={evidenceDesc}
                onChange={(e) => setEvidenceDesc(e.target.value)}
                rows={2}
                placeholder="Briefly describe the contents of this document..."
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">Institutional Attestation Notes</label>
              <textarea
                value={submissionNotes}
                onChange={(e) => setSubmissionNotes(e.target.value)}
                rows={2}
                placeholder="Certification notes on authentic validity of the submitted proof..."
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">Secure Vault Document Key / URL</label>
              <input
                type="text"
                value={fileUrl}
                onChange={(e) => setFileUrl(e.target.value)}
                placeholder="/vault/compliance/evidence_2026.pdf"
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs font-mono"
              />
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setIsEvidenceModalOpen(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={evidenceMutation.isPending}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded disabled:opacity-50"
              >
                {evidenceMutation.isPending ? 'Submitting...' : 'Upload & Submit'}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Officer Review Modal */}
      {isReviewModalOpen && (
        <Modal
          isOpen={isReviewModalOpen}
          onClose={() => setIsReviewModalOpen(false)}
          title="Officer Scrutiny & Determination"
        >
          <form onSubmit={handleReviewSubmit} className="space-y-4 text-xs">
            {reviewError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-700 rounded text-xs flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 flex-shrink-0" />
                {reviewError}
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-bold mb-1">Review Determination *</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => setReviewDecision('VERIFIED_COMPLIANT')}
                  className={`p-2 rounded border text-center font-semibold transition-all ${
                    reviewDecision === 'VERIFIED_COMPLIANT'
                      ? 'border-emerald-600 bg-emerald-50 text-emerald-800 ring-2 ring-emerald-400'
                      : 'border-slate-300 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <CheckCircle2 className="w-4 h-4 mx-auto mb-1 text-emerald-600" />
                  Verified Compliant
                </button>

                <button
                  type="button"
                  onClick={() => setReviewDecision('DEFICIENCY_FLAGGED')}
                  className={`p-2 rounded border text-center font-semibold transition-all ${
                    reviewDecision === 'DEFICIENCY_FLAGGED'
                      ? 'border-amber-600 bg-amber-50 text-amber-800 ring-2 ring-amber-400'
                      : 'border-slate-300 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <AlertTriangle className="w-4 h-4 mx-auto mb-1 text-amber-600" />
                  Flag Deficiency
                </button>

                <button
                  type="button"
                  onClick={() => setReviewDecision('CLOSED')}
                  className={`p-2 rounded border text-center font-semibold transition-all ${
                    reviewDecision === 'CLOSED'
                      ? 'border-slate-600 bg-slate-100 text-slate-800 ring-2 ring-slate-400'
                      : 'border-slate-300 hover:bg-slate-50 text-slate-700'
                  }`}
                >
                  <XCircle className="w-4 h-4 mx-auto mb-1 text-slate-600" />
                  Close Obligation
                </button>
              </div>
            </div>

            {reviewDecision === 'DEFICIENCY_FLAGGED' && (
              <div>
                <label className="block text-slate-700 font-bold mb-1">Cure Period Extension (Days)</label>
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={deficiencyCureDays}
                  onChange={(e) => setDeficiencyCureDays(Number(e.target.value))}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
                <span className="text-[10px] text-slate-500 mt-0.5 block">
                  Cure window granted under APH Clause 6.3.2 guidelines.
                </span>
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-bold mb-1">Scrutiny Findings & Review Remarks *</label>
              <textarea
                value={reviewComments}
                onChange={(e) => setReviewComments(e.target.value)}
                rows={3}
                placeholder="State verified compliance grounds or specify exact deficiency findings for the institution to cure..."
                required
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setIsReviewModalOpen(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={reviewMutation.isPending}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded disabled:opacity-50"
              >
                {reviewMutation.isPending ? 'Recording...' : 'Record Determination'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
