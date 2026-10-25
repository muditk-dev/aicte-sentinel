import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { applicationService } from '../services/applicationService'
import { documentService } from '../services/documentService'
import { scrutinyService } from '../services/scrutinyService'
import { deficiencyService } from '../services/deficiencyService'
import { evcService } from '../services/evcService'
import { decisionService } from '../services/decisionService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import { Document } from '../types'
import {
  ArrowLeft,
  AlertTriangle,
  History,
  FileCheck,
  Send,
  Upload,
  Download,
  ShieldCheck,
  ShieldAlert,
  Clock,
  FileText,
  XCircle,
  Plus,
  Info,
  Users,
  Award,
} from 'lucide-react'

export const ApplicationDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()

  const [activeTab, setActiveTab] = useState<'overview' | 'documents' | 'scrutiny' | 'deficiencies' | 'evc' | 'decision' | 'timeline'>('overview')

  // Statutory Transition State
  const [targetStatus, setTargetStatus] = useState('')
  const [transitionRemarks, setTransitionRemarks] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  // Document Upload Modal State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)
  const [uploadCategory, setUploadCategory] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [selectedDocVersions, setSelectedDocVersions] = useState<Document | null>(null)

  // Scrutiny Recording State
  const [scrutinyCategory, setScrutinyCategory] = useState('')
  const [scrutinyDocId, setScrutinyDocId] = useState<string>('')
  const [scrutinyStatus, setScrutinyStatus] = useState<'ACCEPTED' | 'DEFICIENT' | 'REQUIRES_MANUAL_VERIFICATION'>('ACCEPTED')
  const [scrutinyReason, setScrutinyReason] = useState('')
  const [scrutinyNotes, setScrutinyNotes] = useState('')
  const [scrutinyError, setScrutinyError] = useState<string | null>(null)

  // Deficiency Notice Drafting State
  const [isDeficiencyModalOpen, setIsDeficiencyModalOpen] = useState(false)
  const [deficiencyRemarks, setDeficiencyRemarks] = useState('')
  const [cureDays, setCureDays] = useState(7)
  const [deficiencyItems, setDeficiencyItems] = useState<Array<{ requirement_title: string; description: string; required_corrective_action: string; document_id?: string }>>([
    { requirement_title: '', description: '', required_corrective_action: '' },
  ])
  const [deficiencyError, setDeficiencyError] = useState<string | null>(null)

  // Institutional Clarification Response State
  const [isResponseModalOpen, setIsResponseModalOpen] = useState(false)
  const [respondingNoticeId, setRespondingNoticeId] = useState<string | null>(null)
  const [responseRemarks, setResponseRemarks] = useState('')
  const [responseError, setResponseError] = useState<string | null>(null)

  // Queries
  const { data: application, isLoading: appLoading, error: appError } = useQuery({
    queryKey: ['application', id],
    queryFn: () => applicationService.getApplication(id),
    enabled: !!id,
  })

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => documentService.listDocuments(id),
    enabled: !!id,
  })

  const { data: findings = [], isLoading: findingsLoading } = useQuery({
    queryKey: ['scrutiny-findings', id],
    queryFn: () => scrutinyService.listFindings(id),
    enabled: !!id,
  })

  const { data: notices = [], isLoading: noticesLoading } = useQuery({
    queryKey: ['deficiency-notices', id],
    queryFn: () => deficiencyService.listNotices(id),
    enabled: !!id,
  })

  const { data: appInspections = [] } = useQuery({
    queryKey: ['app-inspections', id],
    queryFn: () => evcService.listInspections({ application_id: id }),
    enabled: !!id,
  })

  const { data: appDecision } = useQuery({
    queryKey: ['app-decision', id],
    queryFn: () => decisionService.getDecisionByApplication(id),
    enabled: !!id,
  })

  // Mutations
  const transitionMutation = useMutation({
    mutationFn: (vars: { target_status: string; remarks: string }) =>
      applicationService.transitionState(id, vars),
    onSuccess: (updated) => {
      queryClient.setQueryData(['application', id], updated)
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      queryClient.invalidateQueries({ queryKey: ['audit-verify'] })
      setActionSuccess(`Application transitioned successfully to ${updated.current_status}.`)
      setActionError(null)
      setTargetStatus('')
      setTransitionRemarks('')
    },
    onError: (err: any) => {
      setActionError(err.message || 'Transition blocked by statutory guardrails.')
      setActionSuccess(null)
    },
  })

  const uploadMutation = useMutation({
    mutationFn: (vars: { category: string; file: File }) =>
      documentService.uploadDocument(id, vars.category, vars.file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      setIsUploadModalOpen(false)
      setSelectedFile(null)
      setUploadCategory('')
      setUploadError(null)
    },
    onError: (err: any) => {
      setUploadError(err.message || 'Upload rejected during file validation or antivirus scanning.')
    },
  })

  const scrutinyMutation = useMutation({
    mutationFn: (vars: { category: string; document_id?: string; finding_status: string; reason: string; notes?: string }) =>
      scrutinyService.recordFinding(id, vars),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scrutiny-findings', id] })
      queryClient.invalidateQueries({ queryKey: ['documents', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      setScrutinyReason('')
      setScrutinyNotes('')
      setScrutinyError(null)
    },
    onError: (err: any) => {
      setScrutinyError(err.message || 'Failed to record scrutiny finding.')
    },
  })

  const createNoticeMutation = useMutation({
    mutationFn: (vars: { officer_remarks: string; cure_days: number; items: any[] }) =>
      deficiencyService.createNotice(id, vars),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deficiency-notices', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
      setIsDeficiencyModalOpen(false)
      setDeficiencyRemarks('')
      setDeficiencyItems([{ requirement_title: '', description: '', required_corrective_action: '' }])
      setDeficiencyError(null)
    },
    onError: (err: any) => {
      setDeficiencyError(err.message || 'Failed to issue deficiency notice.')
    },
  })

  const submitResponseMutation = useMutation({
    mutationFn: (vars: { noticeId: string; response_remarks: string }) =>
      deficiencyService.submitResponse(vars.noticeId, { response_remarks: vars.response_remarks }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deficiency-notices', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      setIsResponseModalOpen(false)
      setResponseRemarks('')
      setResponseError(null)
    },
    onError: (err: any) => {
      setResponseError(err.message || 'Failed to submit response.')
    },
  })

  const reviewNoticeMutation = useMutation({
    mutationFn: (vars: { noticeId: string; action: 'RESOLVE' | 'REOPEN'; remarks: string }) =>
      deficiencyService.reviewNotice(vars.noticeId, { action: vars.action, officer_remarks: vars.remarks }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deficiency-notices', id] })
      queryClient.invalidateQueries({ queryKey: ['application', id] })
      queryClient.invalidateQueries({ queryKey: ['notifications'] })
    },
  })

  if (appLoading) {
    return <div className="p-8 text-center text-slate-500 text-xs">Loading statutory docket details...</div>
  }

  if (appError || !application) {
    return <div className="p-8 text-center text-rose-600 text-xs">Failed to load application docket. Access may be restricted.</div>
  }

  const isOfficer = user?.roles.some((r) => ['SUPER_ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER'].includes(r.code))
  const isInstitutionAdmin = user?.roles.some((r) => r.code === 'INSTITUTION_ADMIN')

  // Parse submission payload
  let submissionData: Record<string, any> = {}
  try {
    submissionData = JSON.parse(application.submission_data_json || '{}')
  } catch {
    submissionData = {}
  }

  // Statutory state machine permissible transitions
  const getPermissibleTransitions = (st: string) => {
    switch (st) {
      case 'DRAFT':
        return [{ target: 'SUBMITTED', label: 'Submit Application to Council' }]
      case 'SUBMITTED':
        return [{ target: 'UNDER_SCRUTINY', label: 'Initiate Document Scrutiny' }]
      case 'UNDER_SCRUTINY':
        return [
          { target: 'DEFICIENCY_ISSUED', label: 'Issue Statutory Deficiency Notice' },
          { target: 'EVC_SCHEDULED', label: 'Schedule Physical/Virtual EVC Inspection' },
          { target: 'RECOMMENDED_APPROVAL', label: 'Clear Scrutiny & Recommend Approval' },
        ]
      case 'DEFICIENCY_ISSUED':
        return [{ target: 'RESUBMITTED', label: 'Submit Clarification & Rectified Documents' }]
      case 'RESUBMITTED':
        return [{ target: 'UNDER_SCRUTINY', label: 'Resume Scrutiny on Resubmission' }]
      case 'EVC_SCHEDULED':
        return [{ target: 'EVC_CONDUCTED', label: 'Upload & Submit EVC Inspection Report' }]
      case 'EVC_CONDUCTED':
        return [
          { target: 'RECOMMENDED_APPROVAL', label: 'Recommend for Approval (Clear EVC)' },
          { target: 'STANDING_HEARING', label: 'Refer to Standing Hearing Committee (Deficient EVC)' },
        ]
      case 'STANDING_HEARING':
        return [
          { target: 'RECOMMENDED_APPROVAL', label: 'Clear Docket on Hearing' },
          { target: 'REJECTED', label: 'Reject Application post Hearing' },
        ]
      case 'RECOMMENDED_APPROVAL':
        return [
          { target: 'APPROVED', label: 'Grant Statutory Approval (AICTE Council)' },
          { target: 'REJECTED', label: 'Reject Statutory Approval' },
        ]
      default:
        return []
    }
  }

  const permissible = getPermissibleTransitions(application.current_status)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0]
      if (f.size > 15 * 1024 * 1024) {
        setUploadError('File exceeds statutory limit of 15 MB')
        setSelectedFile(null)
      } else {
        setUploadError(null)
        setSelectedFile(f)
      }
    }
  }

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadCategory || !selectedFile) {
      setUploadError('Please select both category and valid file.')
      return
    }
    uploadMutation.mutate({ category: uploadCategory, file: selectedFile })
  }

  const handleExecuteTransition = (e: React.FormEvent) => {
    e.preventDefault()
    if (!targetStatus) {
      setActionError('Please select a target statutory state.')
      return
    }
    if (!transitionRemarks.trim()) {
      setActionError('Statutory regulations mandate entering recorded remarks.')
      return
    }
    transitionMutation.mutate({ target_status: targetStatus, remarks: transitionRemarks })
  }

  const handleAddDeficiencyItem = () => {
    setDeficiencyItems([...deficiencyItems, { requirement_title: '', description: '', required_corrective_action: '' }])
  }

  const handleDeficiencySubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!deficiencyRemarks.trim()) {
      setDeficiencyError('Official remarks are required.')
      return
    }
    for (const item of deficiencyItems) {
      if (!item.requirement_title || !item.description || !item.required_corrective_action) {
        setDeficiencyError('All deficiency fields must be completed.')
        return
      }
    }
    createNoticeMutation.mutate({
      officer_remarks: deficiencyRemarks,
      cure_days: cureDays,
      items: deficiencyItems,
    })
  }

  const handleResponseSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!respondingNoticeId || !responseRemarks.trim()) {
      setResponseError('Official clarification remarks are required.')
      return
    }
    submitResponseMutation.mutate({
      noticeId: respondingNoticeId,
      response_remarks: responseRemarks,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/applications" className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900">
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Applications Registry
        </Link>
      </div>

      {/* Header Docket Summary */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-xl font-bold font-mono text-slate-900">{application.application_number}</h1>
              <StatusBadge status={application.current_status} />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Academic Cycle: <span className="font-semibold text-slate-700">{application.academic_year}</span> • Docket ID: <span className="font-mono text-[11px]">{application.id}</span>
            </p>
          </div>

          <div className="text-left md:text-right">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">SLA Target Deadline</span>
            <span className="font-mono text-xs font-semibold text-slate-800">
              {application.sla_deadline ? formatDate(application.sla_deadline) : 'Standard 30-Day Window'}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 mt-4 -mb-2 space-x-4 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('overview')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'overview'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <FileText className="w-3.5 h-3.5 mr-1.5" />
            Overview & Decisions
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'documents'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 mr-1.5" />
            Document Checklist ({documents.length})
          </button>
          <button
            onClick={() => setActiveTab('scrutiny')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'scrutiny'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <FileCheck className="w-3.5 h-3.5 mr-1.5" />
            Scrutiny Workspace ({findings.length})
          </button>
          <button
            onClick={() => setActiveTab('deficiencies')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'deficiencies'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
            Deficiency Notices ({notices.length})
          </button>
          <button
            onClick={() => setActiveTab('evc')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'evc'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Users className="w-3.5 h-3.5 mr-1.5" />
            EVC Inspections ({appInspections.length})
          </button>
          <button
            onClick={() => setActiveTab('decision')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'decision'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <Award className="w-3.5 h-3.5 mr-1.5" />
            Statutory Determination {appDecision ? '(Rendered)' : ''}
          </button>
          <button
            onClick={() => setActiveTab('timeline')}
            className={`pb-3 px-1 border-b-2 flex items-center transition-colors ${
              activeTab === 'timeline'
                ? 'border-blue-700 text-blue-700'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            <History className="w-3.5 h-3.5 mr-1.5" />
            Audit & Timeline ({application.events.length})
          </button>
        </div>
      </div>

      {/* TAB 1: OVERVIEW & STATE TRANSITIONS */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center">
                  <FileCheck className="w-4 h-4 mr-1.5 text-blue-700" />
                  Statutory Decision Action Desk
                </h2>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
                  Guarded State Machine
                </span>
              </div>

              {actionError && <div className="mt-3 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs">{actionError}</div>}
              {actionSuccess && <div className="mt-3 bg-emerald-50 border-l-4 border-emerald-500 p-3 rounded text-emerald-800 text-xs">{actionSuccess}</div>}

              {permissible.length === 0 ? (
                <div className="mt-4 p-4 rounded bg-slate-50 border border-slate-200 text-center text-xs text-slate-600">
                  This application docket is in terminal or pending state ({application.current_status}). No further direct state transitions permissible.
                </div>
              ) : (
                <form onSubmit={handleExecuteTransition} className="mt-4 space-y-4 text-xs">
                  <div>
                    <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Select Statutory Transition</label>
                    <select
                      value={targetStatus}
                      onChange={(e) => setTargetStatus(e.target.value)}
                      required
                      className="w-full border border-slate-300 rounded-md p-2 bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-600 text-xs"
                    >
                      <option value="">Select statutory action...</option>
                      {permissible.map((p) => (
                        <option key={p.target} value={p.target}>{p.label} (→ {p.target})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Official Statutory Remarks / Attestation</label>
                    <textarea
                      rows={3}
                      value={transitionRemarks}
                      onChange={(e) => setTransitionRemarks(e.target.value)}
                      placeholder="Enter regulatory rationale under APH..."
                      required
                      className="w-full border border-slate-300 rounded-md p-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-600"
                    />
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      type="submit"
                      disabled={transitionMutation.isPending}
                      className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5 mr-1.5" />
                      {transitionMutation.isPending ? 'Executing...' : 'Record Statutory Transition'}
                    </button>
                  </div>
                </form>
              )}
            </div>

            <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Application Intake Submission Parameters</h3>
              <div className="bg-slate-50 rounded border border-slate-200 p-4 font-mono text-xs overflow-x-auto text-slate-800">
                <pre>{JSON.stringify(submissionData, null, 2)}</pre>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3 flex items-center">
                <Clock className="w-4 h-4 mr-1.5 text-blue-700" />
                Key Regulatory Dates
              </h3>
              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span>Intake Submission:</span>
                  <span className="font-mono text-slate-800">{formatDate(application.submission_date || application.created_at)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-100">
                  <span>SLA Processing Deadline:</span>
                  <span className="font-mono text-slate-800">{application.sla_deadline ? formatDate(application.sla_deadline) : 'Within standard window'}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>Active Cycle:</span>
                  <span className="font-semibold text-blue-700">{application.academic_year}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DOCUMENT CHECKLIST & UPLOAD */}
      {activeTab === 'documents' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Statutory Document Vault</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Uploaded documents undergo byte-level file signature inspection and ClamAV quarantine scanning before vault promotion.
              </p>
            </div>

            <button
              onClick={() => {
                setUploadError(null)
                setIsUploadModalOpen(true)
              }}
              className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 transition-colors"
            >
              <Upload className="w-4 h-4 mr-1.5" />
              Upload Regulatory Document
            </button>
          </div>

          {/* Document Table */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                <thead className="bg-slate-100 text-slate-600 font-bold uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-4 py-3">File Name</th>
                    <th className="px-4 py-3">Version</th>
                    <th className="px-4 py-3">Size</th>
                    <th className="px-4 py-3">SHA-256 Digest</th>
                    <th className="px-4 py-3">Security & Antivirus</th>
                    <th className="px-4 py-3">Scrutiny State</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 bg-white">
                  {docsLoading ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">Loading documents...</td></tr>
                  ) : documents.length === 0 ? (
                    <tr><td colSpan={8} className="px-4 py-8 text-center text-slate-500">No documents uploaded for this application docket yet.</td></tr>
                  ) : (
                    documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-900">{doc.category}</td>
                        <td className="px-4 py-3 text-slate-600 truncate max-w-[180px]" title={doc.original_filename}>{doc.original_filename}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setSelectedDocVersions(doc)}
                            className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 hover:bg-slate-200"
                          >
                            v{doc.current_version}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-slate-500 font-mono text-[11px]">{(doc.file_size / 1024).toFixed(1)} KB</td>
                        <td className="px-4 py-3 font-mono text-[10px] text-slate-600 truncate max-w-[120px]" title={doc.sha256_hash}>
                          {doc.sha256_hash.substring(0, 10)}...
                        </td>
                        <td className="px-4 py-3">
                          {doc.scan_status === 'ACCEPTED' ? (
                            <span className="inline-flex items-center text-[10px] font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                              <ShieldCheck className="w-3 h-3 mr-1 text-emerald-600" />
                              CLEAN
                            </span>
                          ) : doc.scan_status === 'REJECTED' ? (
                            <span className="inline-flex items-center text-[10px] font-bold text-rose-800 bg-rose-50 px-2 py-0.5 rounded border border-rose-200" title={doc.rejection_reason}>
                              <XCircle className="w-3 h-3 mr-1 text-rose-600" />
                              REJECTED
                            </span>
                          ) : (
                            <span className="inline-flex items-center text-[10px] font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                              <ShieldAlert className="w-3 h-3 mr-1 text-amber-600" />
                              QUARANTINED
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center text-[10px] font-bold px-2 py-0.5 rounded ${
                            doc.verification_status === 'ACCEPTED'
                              ? 'bg-teal-50 text-teal-800 border border-teal-200'
                              : doc.verification_status === 'DEFICIENT'
                              ? 'bg-rose-50 text-rose-800 border border-rose-200'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
                          }`}>
                            {doc.verification_status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => documentService.downloadDocument(doc.id, doc.original_filename)}
                            disabled={doc.scan_status !== 'ACCEPTED'}
                            title={doc.scan_status !== 'ACCEPTED' ? 'Quarantined files cannot be downloaded' : 'Download clean file'}
                            className="inline-flex items-center text-xs font-semibold text-blue-700 hover:text-blue-900 disabled:opacity-40 disabled:cursor-not-allowed"
                          >
                            <Download className="w-3.5 h-3.5 mr-1" />
                            Download
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SCRUTINY WORKSPACE */}
      {activeTab === 'scrutiny' && (
        <div className="space-y-6">
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-xs text-amber-900 flex items-start space-x-2">
            <Info className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
            <p className="text-[11px] leading-relaxed">
              <strong>Statutory Scrutiny Desk:</strong> All scrutiny findings require verified human determination under APH norms. AI assistance is strictly informational and advisory.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Record Finding Form (Officers Only) */}
            {isOfficer && (
              <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Record Official Scrutiny Finding</h3>

                {scrutinyError && <div className="mb-3 bg-rose-50 border-l-4 border-rose-500 p-2 text-rose-800 text-xs">{scrutinyError}</div>}

                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    if (!scrutinyCategory || !scrutinyReason) {
                      setScrutinyError('Category and reason are required.')
                      return
                    }
                    scrutinyMutation.mutate({
                      category: scrutinyCategory,
                      document_id: scrutinyDocId || undefined,
                      finding_status: scrutinyStatus,
                      reason: scrutinyReason,
                      notes: scrutinyNotes,
                    })
                  }}
                  className="space-y-3 text-xs"
                >
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Target Category / Requirement</label>
                    <input
                      type="text"
                      value={scrutinyCategory}
                      onChange={(e) => setScrutinyCategory(e.target.value)}
                      placeholder="e.g. Land Title Deed, Faculty Cadre Ratio"
                      required
                      className="w-full border border-slate-300 rounded p-2 text-xs"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Link to Uploaded Document</label>
                    <select
                      value={scrutinyDocId}
                      onChange={(e) => setScrutinyDocId(e.target.value)}
                      className="w-full border border-slate-300 rounded p-2 text-xs bg-white"
                    >
                      <option value="">None / General Requirement</option>
                      {documents.map((d) => (
                        <option key={d.id} value={d.id}>{d.category} ({d.original_filename})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Scrutiny Determination</label>
                    <select
                      value={scrutinyStatus}
                      onChange={(e) => setScrutinyStatus(e.target.value as any)}
                      className="w-full border border-slate-300 rounded p-2 text-xs bg-white"
                    >
                      <option value="ACCEPTED">ACCEPTED (Meets APH Norms)</option>
                      <option value="DEFICIENT">DEFICIENT (Statutory Non-Compliance)</option>
                      <option value="REQUIRES_MANUAL_VERIFICATION">REQUIRES MANUAL VERIFICATION</option>
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Statutory Rationale / Reason</label>
                    <textarea
                      rows={2}
                      value={scrutinyReason}
                      onChange={(e) => setScrutinyReason(e.target.value)}
                      placeholder="Specify clause under APH..."
                      required
                      className="w-full border border-slate-300 rounded p-2 text-xs"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Internal Notes</label>
                    <textarea
                      rows={2}
                      value={scrutinyNotes}
                      onChange={(e) => setScrutinyNotes(e.target.value)}
                      placeholder="Supporting notes for committee..."
                      className="w-full border border-slate-300 rounded p-2 text-xs"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={scrutinyMutation.isPending}
                    className="w-full py-2 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded shadow-sm disabled:opacity-50"
                  >
                    {scrutinyMutation.isPending ? 'Recording...' : 'Commit Scrutiny Finding'}
                  </button>
                </form>
              </div>
            )}

            {/* Findings List */}
            <div className={`${isOfficer ? 'lg:col-span-2' : 'lg:col-span-3'} space-y-4`}>
              <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">Recorded Scrutiny Findings</h3>

                {findingsLoading ? (
                  <p className="text-xs text-slate-500">Loading findings...</p>
                ) : findings.length === 0 ? (
                  <p className="text-xs text-slate-500">No scrutiny findings recorded yet.</p>
                ) : (
                  <div className="space-y-3">
                    {findings.map((f) => (
                      <div key={f.id} className="p-3.5 rounded border border-slate-200 bg-slate-50 text-xs space-y-1.5">
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-slate-900">{f.category}</span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            f.finding_status === 'ACCEPTED'
                              ? 'bg-emerald-100 text-emerald-800'
                              : f.finding_status === 'DEFICIENT'
                              ? 'bg-rose-100 text-rose-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}>
                            {f.finding_status}
                          </span>
                        </div>
                        <p className="text-slate-700">{f.reason}</p>
                        {f.notes && <p className="text-[11px] text-slate-500 italic">Notes: {f.notes}</p>}
                        <div className="text-[10px] text-slate-400 font-mono pt-1">
                          Recorded on {formatDate(f.created_at)}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: DEFICIENCY NOTICES & CLARIFICATION */}
      {activeTab === 'deficiencies' && (
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">Statutory Deficiency & Clarification Desk</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Deficiency notices grant institutions a legally mandated cure window to provide clarifications and replacement evidence.
              </p>
            </div>

            {isOfficer && (
              <button
                onClick={() => {
                  setDeficiencyError(null)
                  setIsDeficiencyModalOpen(true)
                }}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 transition-colors"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Draft Formal Deficiency Notice
              </button>
            )}
          </div>

          {/* Notices List */}
          {noticesLoading ? (
            <p className="text-xs text-slate-500">Loading notices...</p>
          ) : notices.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-xs text-slate-500">
              No formal deficiency notices issued for this application docket.
            </div>
          ) : (
            notices.map((notice) => {
              const now = new Date()
              const dueDate = new Date(notice.due_date)
              const isOverdue = now > dueDate && notice.status !== 'RESOLVED'

              return (
                <div key={notice.id} className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-slate-100">
                    <div>
                      <div className="flex items-center space-x-3">
                        <span className="font-mono text-sm font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          {notice.notice_number}
                        </span>
                        <StatusBadge status={notice.status} />
                        {isOverdue && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-200">
                            CURE DEADLINE EXPIRED
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 mt-1">{notice.officer_remarks}</p>
                    </div>

                    <div className="text-right text-xs">
                      <span className="text-slate-500 block text-[11px]">Mandatory Statutory Due Date</span>
                      <span className="font-mono font-bold text-slate-800">{formatDate(notice.due_date)}</span>
                    </div>
                  </div>

                  {/* Items list */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">Flagged Deficiency Items ({notice.items.length})</h4>
                    <div className="space-y-2">
                      {notice.items.map((it) => (
                        <div key={it.id} className="p-3 rounded border border-slate-200 bg-slate-50 text-xs space-y-1">
                          <div className="flex justify-between items-center font-bold text-slate-900">
                            <span>{it.requirement_title}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${it.item_status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}`}>
                              {it.item_status}
                            </span>
                          </div>
                          <p className="text-slate-700"><strong className="text-slate-800">Deficiency:</strong> {it.description}</p>
                          <p className="text-slate-700"><strong className="text-slate-800">Required Corrective Action:</strong> {it.required_corrective_action}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Responses */}
                  {notice.responses.length > 0 && (
                    <div className="pt-2 border-t border-slate-100">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">Institutional Response</h4>
                      {notice.responses.map((resp) => (
                        <div key={resp.id} className="p-3 rounded bg-blue-50/60 border border-blue-200 text-xs">
                          <p className="text-slate-800 font-medium">{resp.response_remarks}</p>
                          <span className="text-[10px] text-slate-500 font-mono mt-1 block">Submitted on {formatDate(resp.created_at)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Action Controls */}
                  <div className="pt-3 border-t border-slate-100 flex justify-end space-x-3">
                    {/* Institution Response Button */}
                    {isInstitutionAdmin && ['ISSUED', 'REOPENED'].includes(notice.status) && (
                      <button
                        onClick={() => {
                          setRespondingNoticeId(notice.id)
                          setResponseError(null)
                          setIsResponseModalOpen(true)
                        }}
                        className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold rounded shadow-sm"
                      >
                        Submit Institutional Clarification
                      </button>
                    )}

                    {/* Officer Review Controls */}
                    {isOfficer && notice.status === 'RESPONSE_SUBMITTED' && (
                      <>
                        <button
                          onClick={() => {
                            const r = prompt('Enter resolution remarks:')
                            if (r) reviewNoticeMutation.mutate({ noticeId: notice.id, action: 'RESOLVE', remarks: r })
                          }}
                          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-semibold rounded shadow-sm"
                        >
                          Resolve & Clear Deficiency Notice
                        </button>
                        <button
                          onClick={() => {
                            const r = prompt('Enter reopening remarks (new 7-day cure window):')
                            if (r) reviewNoticeMutation.mutate({ noticeId: notice.id, action: 'REOPEN', remarks: r })
                          }}
                          className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white text-xs font-semibold rounded shadow-sm"
                        >
                          Reopen for Further Clarification
                        </button>
                      </>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}

      {/* TAB: EVC INSPECTIONS */}
      {activeTab === 'evc' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center bg-white p-4 rounded-lg border border-slate-200">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center">
                <Users className="w-4 h-4 mr-1.5 text-blue-700" />
                Expert Visit Committee (EVC) Physical & Virtual Inspections
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Statutory inspection panels, verified conflict checks, and versioned reports for this docket.
              </p>
            </div>
            <Link
              to="/evc"
              className="text-xs font-semibold px-3 py-1.5 bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100"
            >
              Open EVC Desk →
            </Link>
          </div>

          {appInspections.length === 0 ? (
            <div className="bg-white rounded-lg border border-slate-200 p-12 text-center text-slate-500 text-xs">
              <Users className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              <p className="font-semibold text-slate-700">No EVC inspections scheduled for this docket</p>
              <p className="mt-1">Applications requiring physical or virtual on-site verification will have panels assigned by the Regional Office.</p>
            </div>
          ) : (
            appInspections.map((insp) => (
              <div key={insp.id} className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono font-bold text-sm text-blue-800">{insp.inspection_number}</span>
                    <StatusBadge status={insp.status} />
                    <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 rounded text-slate-700">
                      {insp.inspection_mode}
                    </span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">
                    {formatDate(insp.scheduled_start_date)} — {formatDate(insp.scheduled_end_date)}
                  </span>
                </div>

                {/* Panel Members */}
                <div>
                  <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Inspection Panel Members ({insp.panel_members.length})</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {insp.panel_members.map((pm) => (
                      <div key={pm.id} className="p-3 bg-slate-50 rounded border border-slate-200 text-xs space-y-1">
                        <div className="flex justify-between font-bold">
                          <span>{pm.expert_name} ({pm.role})</span>
                          <span className={pm.conflict_check_passed ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>
                            {pm.conflict_check_passed ? '✓ COI Cleared' : '✗ Conflict'}
                          </span>
                        </div>
                        <div className="text-slate-600">{pm.expert_designation} — {pm.expert_organization}</div>
                        {pm.conflict_notes && (
                          <div className="text-amber-800 bg-amber-50 p-1.5 rounded text-[11px]">
                            <strong>Exemption:</strong> {pm.conflict_notes}
                          </div>
                        )}
                        <div className="text-[11px] text-slate-500 flex justify-between pt-1">
                          <span>Attendance: {pm.attendance_status}</span>
                          <span>Sign-off: {pm.sign_off_status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Latest Report Verdict */}
                {insp.latest_report && (
                  <div className="p-4 bg-blue-50/60 rounded border border-blue-200 text-xs space-y-2">
                    <div className="flex justify-between items-center font-bold">
                      <span className="text-slate-800">
                        EVC Report Version {insp.latest_report.version_number}:{' '}
                        <span className={insp.latest_report.overall_recommendation === 'RECOMMENDED' ? 'text-emerald-700' : 'text-rose-700'}>
                          {insp.latest_report.overall_recommendation}
                        </span>{' '}
                        (Score: {insp.latest_report.infrastructure_score}/100)
                      </span>
                      <StatusBadge status={insp.latest_report.review_status} />
                    </div>
                    <p className="text-slate-700">{insp.latest_report.observations}</p>
                    <div className="font-mono text-[10px] text-slate-500">
                      Payload SHA-256 Digest: {insp.latest_report.sha256_hash}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* TAB: STATUTORY DETERMINATION */}
      {activeTab === 'decision' && (
        <div className="space-y-4">
          {appDecision ? (
            <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm space-y-5">
              <div className="flex justify-between items-start pb-4 border-b border-slate-200">
                <div>
                  <div className="flex items-center space-x-3">
                    <h3 className="text-lg font-bold font-mono text-slate-900">{appDecision.decision_number}</h3>
                    <StatusBadge status={appDecision.decision_type} />
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-100 font-semibold text-slate-700">
                      AY {appDecision.academic_year}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Statutorily authorized by <strong>{appDecision.authorized_by_name}</strong> ({appDecision.authority_role}) on {formatDate(appDecision.authorized_at)}
                  </p>
                </div>
                {appDecision.intake_approved && (
                  <div className="text-right">
                    <span className="text-[11px] font-bold text-slate-500 uppercase block">Approved Intake</span>
                    <span className="text-base font-bold text-blue-700">{appDecision.intake_approved} Seats</span>
                  </div>
                )}
              </div>

              {/* Official Findings */}
              <div className="space-y-1 text-xs">
                <span className="font-bold text-slate-700 uppercase tracking-wider">Statutory Reasons & Grounding:</span>
                <p className="p-3 bg-slate-50 rounded border border-slate-200 text-slate-800 leading-relaxed">
                  {appDecision.reasons}
                </p>
              </div>

              {/* Conditions */}
              {appDecision.conditions && appDecision.conditions.length > 0 && (
                <div className="space-y-2 text-xs">
                  <span className="font-bold text-amber-800 uppercase tracking-wider">
                    Mandatory Compliance Conditions ({appDecision.conditions.length}):
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {appDecision.conditions.map((cond) => (
                      <div key={cond.id} className="p-3 bg-amber-50 border border-amber-200 rounded space-y-1">
                        <div className="flex justify-between font-bold text-amber-900">
                          <span>{cond.condition_code}</span>
                          <span className="text-[11px] font-semibold text-amber-700">Due: {formatDate(cond.due_date)}</span>
                        </div>
                        <p className="text-amber-800 text-[11px]">{cond.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Human Attestation */}
              <div className="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-900 space-y-1">
                <div className="font-bold flex items-center">
                  <ShieldCheck className="w-4 h-4 mr-1 text-blue-700" />
                  Officer Non-Repudiation Attestation
                </div>
                <p className="text-[11px] italic leading-relaxed">{appDecision.declaration_text}</p>
              </div>

              {/* SHA-256 Digest */}
              <div className="pt-2 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-center text-[11px] text-slate-500 font-mono gap-2">
                <span>SHA-256 Attestation: {appDecision.sha256_attestation}</span>
                <span className="text-slate-600 font-sans font-medium">Policy: {appDecision.governing_policy_version}</span>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-500 text-xs space-y-3">
              <Award className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="font-semibold text-slate-700 text-sm">No final statutory determination rendered yet</p>
              <p className="max-w-md mx-auto">
                Once document scrutiny and any applicable EVC inspections or committee hearings are concluded, authorized regional officers or council members issue the formal determination.
              </p>
              {isOfficer && (
                <div className="pt-2">
                  <Link
                    to="/decisions"
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded text-xs font-semibold hover:bg-blue-700"
                  >
                    Open Statutory Decisions Desk →
                  </Link>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 5: AUDIT & TIMELINE */}
      {activeTab === 'timeline' && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-4 flex items-center">
            <History className="w-4 h-4 mr-1.5 text-blue-700" />
            Statutory Application Lifecycle Audit Trail
          </h3>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
            {application.events.map((ev) => (
              <div key={ev.id} className="relative text-xs">
                <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                <div>
                  <div className="font-bold text-slate-900">{ev.event_type}</div>
                  <div className="text-[11px] text-slate-500 font-mono">{formatDate(ev.created_at)}</div>
                  {ev.remarks && (
                    <p className="mt-1 text-slate-700 bg-slate-50 p-2 rounded border border-slate-200 text-[11px]">
                      "{ev.remarks}"
                    </p>
                  )}
                  {ev.to_status && (
                    <div className="mt-1">
                      <StatusBadge status={ev.to_status} />
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* UPLOAD DOCUMENT MODAL */}
      <Modal isOpen={isUploadModalOpen} onClose={() => setIsUploadModalOpen(false)} title="Upload Regulatory Document">
        {uploadError && <div className="mb-4 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs">{uploadError}</div>}

        <form onSubmit={handleUploadSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Document Category</label>
            <select
              value={uploadCategory}
              onChange={(e) => setUploadCategory(e.target.value)}
              required
              className="w-full border border-slate-300 rounded p-2 bg-white text-xs"
            >
              <option value="">Select category...</option>
              <option value="Land Title & Conversion Certificate">Land Title & Conversion Certificate</option>
              <option value="Building Plan & Occupancy Certificate">Building Plan & Occupancy Certificate</option>
              <option value="Faculty Roster with Cadre Ratio">Faculty Roster with Cadre Ratio</option>
              <option value="FDR / Corpus Deposit Verification">FDR / Corpus Deposit Verification</option>
              <option value="Fire Safety NOC & Environmental Clearance">Fire Safety NOC & Environmental Clearance</option>
              <option value="Barrier-Free Ramp & Accessibility">Barrier-Free Ramp & Accessibility</option>
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Select File (PDF, JPEG, PNG • Max 15 MB)</label>
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileChange}
              required
              className="w-full border border-slate-300 rounded p-2 text-xs"
            />
            <p className="text-[11px] text-slate-500 mt-1">Files undergo magic-byte signature check and quarantine antivirus scanning.</p>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
            <button type="button" onClick={() => setIsUploadModalOpen(false)} className="px-3 py-2 border border-slate-300 rounded text-slate-700">Cancel</button>
            <button
              type="submit"
              disabled={uploadMutation.isPending || !selectedFile}
              className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded disabled:opacity-50"
            >
              {uploadMutation.isPending ? 'Verifying & Scanning...' : 'Upload Document'}
            </button>
          </div>
        </form>
      </Modal>

      {/* DOCUMENT VERSIONS MODAL */}
      <Modal isOpen={!!selectedDocVersions} onClose={() => setSelectedDocVersions(null)} title={`Version History: ${selectedDocVersions?.category}`}>
        <div className="space-y-3 text-xs">
          {selectedDocVersions?.versions.map((ver) => (
            <div key={ver.id} className="p-3 rounded border border-slate-200 bg-slate-50 flex justify-between items-center">
              <div>
                <span className="font-bold text-slate-900">Version {ver.version_number}</span>
                <span className="text-[11px] text-slate-500 block font-mono">Uploaded on {formatDate(ver.created_at)}</span>
                <span className="text-[10px] text-slate-400 font-mono">SHA-256: {ver.sha256_hash.substring(0, 16)}...</span>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                {ver.scan_status}
              </span>
            </div>
          ))}
        </div>
      </Modal>

      {/* DRAFT DEFICIENCY NOTICE MODAL */}
      <Modal isOpen={isDeficiencyModalOpen} onClose={() => setIsDeficiencyModalOpen(false)} title="Draft Statutory Deficiency Notice" maxWidth="max-w-2xl">
        {deficiencyError && <div className="mb-4 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs">{deficiencyError}</div>}

        <form onSubmit={handleDeficiencySubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Official Remarks / Statutory Scope</label>
            <textarea
              rows={2}
              value={deficiencyRemarks}
              onChange={(e) => setDeficiencyRemarks(e.target.value)}
              placeholder="State the regulatory background under APH..."
              required
              className="w-full border border-slate-300 rounded p-2 text-xs"
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Statutory Cure Window (Days)</label>
            <input
              type="number"
              value={cureDays}
              onChange={(e) => setCureDays(Number(e.target.value))}
              required
              min={1}
              max={30}
              className="w-32 border border-slate-300 rounded p-2 text-xs"
            />
          </div>

          <div className="border-t border-slate-200 pt-3">
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-slate-700 uppercase tracking-wider">Deficiency Items</span>
              <button type="button" onClick={handleAddDeficiencyItem} className="text-blue-700 font-semibold flex items-center hover:underline">
                <Plus className="w-3 h-3 mr-1" /> Add Item
              </button>
            </div>

            <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
              {deficiencyItems.map((item, idx) => (
                <div key={idx} className="p-3 rounded border border-slate-200 bg-slate-50 space-y-2">
                  <input
                    type="text"
                    placeholder="Requirement Title (e.g. Land conversion NOC)"
                    value={item.requirement_title}
                    onChange={(e) => {
                      const updated = [...deficiencyItems]
                      updated[idx].requirement_title = e.target.value
                      setDeficiencyItems(updated)
                    }}
                    required
                    className="w-full border border-slate-300 rounded p-1.5 text-xs"
                  />
                  <textarea
                    rows={2}
                    placeholder="Deficiency Description..."
                    value={item.description}
                    onChange={(e) => {
                      const updated = [...deficiencyItems]
                      updated[idx].description = e.target.value
                      setDeficiencyItems(updated)
                    }}
                    required
                    className="w-full border border-slate-300 rounded p-1.5 text-xs"
                  />
                  <textarea
                    rows={2}
                    placeholder="Required Corrective Action from Institution..."
                    value={item.required_corrective_action}
                    onChange={(e) => {
                      const updated = [...deficiencyItems]
                      updated[idx].required_corrective_action = e.target.value
                      setDeficiencyItems(updated)
                    }}
                    required
                    className="w-full border border-slate-300 rounded p-1.5 text-xs"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
            <button type="button" onClick={() => setIsDeficiencyModalOpen(false)} className="px-3 py-2 border border-slate-300 rounded text-slate-700">Cancel</button>
            <button
              type="submit"
              disabled={createNoticeMutation.isPending}
              className="px-4 py-2 bg-amber-700 hover:bg-amber-800 text-white font-semibold rounded disabled:opacity-50"
            >
              {createNoticeMutation.isPending ? 'Issuing...' : 'Issue Statutory Notice'}
            </button>
          </div>
        </form>
      </Modal>

      {/* SUBMIT INSTITUTIONAL RESPONSE MODAL */}
      <Modal isOpen={isResponseModalOpen} onClose={() => setIsResponseModalOpen(false)} title="Submit Clarification & Response">
        {responseError && <div className="mb-4 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs">{responseError}</div>}

        <form onSubmit={handleResponseSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">Official Response & Corrective Remarks</label>
            <textarea
              rows={4}
              value={responseRemarks}
              onChange={(e) => setResponseRemarks(e.target.value)}
              placeholder="Detail the corrective actions taken, attached certificates, and compliance points..."
              required
              className="w-full border border-slate-300 rounded p-2 text-xs"
            />
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
            <button type="button" onClick={() => setIsResponseModalOpen(false)} className="px-3 py-2 border border-slate-300 rounded text-slate-700">Cancel</button>
            <button
              type="submit"
              disabled={submitResponseMutation.isPending}
              className="px-4 py-2 bg-blue-700 hover:bg-blue-800 text-white font-semibold rounded disabled:opacity-50"
            >
              {submitResponseMutation.isPending ? 'Submitting...' : 'Submit Clarification'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
