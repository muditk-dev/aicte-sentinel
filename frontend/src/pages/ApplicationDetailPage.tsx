import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { applicationService } from '../services/applicationService'
import { StatusBadge } from '../components/StatusBadge'
import { formatDate } from '../lib/utils'
import {
  ArrowLeft,
  AlertTriangle,
  History,
  FileCheck,
  Send,
} from 'lucide-react'

export const ApplicationDetailPage: React.FC = () => {
  const { id = '' } = useParams<{ id: string }>()
  const queryClient = useQueryClient()

  const [targetStatus, setTargetStatus] = useState('')
  const [transitionRemarks, setTransitionRemarks] = useState('')
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionSuccess, setActionSuccess] = useState<string | null>(null)

  const { data: application, isLoading, error } = useQuery({
    queryKey: ['application', id],
    queryFn: () => applicationService.getApplication(id),
    enabled: !!id,
  })

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

  if (isLoading) {
    return (
      <div className="p-8 text-center text-slate-500 text-xs">
        Loading statutory docket details...
      </div>
    )
  }

  if (error || !application) {
    return (
      <div className="p-8 text-center text-rose-600 text-xs">
        Failed to load application docket. Access may be restricted or ID invalid.
      </div>
    )
  }

  // Parse submission payload
  let submissionData: Record<string, any> = {}
  try {
    submissionData = JSON.parse(application.submission_data_json || '{}')
  } catch {
    submissionData = {}
  }

  // Parse delay risk factors
  let riskFactors: any[] = []
  try {
    riskFactors = JSON.parse(application.delay_risk_factors_json || '[]')
  } catch {
    riskFactors = []
  }

  // Calculate permissible next transitions based on current status and role
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
    transitionMutation.mutate({
      target_status: targetStatus,
      remarks: transitionRemarks,
    })
  }

  return (
    <div className="space-y-6">
      {/* Back button & Breadcrumb */}
      <div>
        <Link
          to="/applications"
          className="inline-flex items-center text-xs font-semibold text-slate-600 hover:text-slate-900"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          Back to Applications Registry
        </Link>
      </div>

      {/* Header Docket Summary */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-xl font-bold font-mono text-slate-900">
                {application.application_number}
              </h1>
              <StatusBadge status={application.current_status} />
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Academic Cycle: <span className="font-semibold text-slate-700">{application.academic_year}</span> • Docket ID: <span className="font-mono text-[11px]">{application.id}</span>
            </p>
          </div>

          <div className="text-left md:text-right">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
              SLA Target Deadline
            </span>
            <span className="font-mono text-xs font-semibold text-slate-800">
              {application.sla_deadline ? formatDate(application.sla_deadline) : 'Standard 30-Day Window'}
            </span>
          </div>
        </div>

        {/* Key Attributes Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 text-xs">
          <div>
            <span className="text-slate-500 block text-[11px]">Primary Discipline</span>
            <span className="font-semibold text-slate-800">
              {submissionData.primary_discipline || 'Engineering & Technology'}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Approved/Proposed Intake</span>
            <span className="font-semibold text-slate-800">
              {submissionData.intake_capacity || submissionData.proposed_intake || '360'} Seats
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Submission Date</span>
            <span className="font-mono text-[11px] text-slate-700">
              {formatDate(application.submission_date || application.created_at)}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[11px]">Delay-Risk (Advisory)</span>
            <span className="font-semibold text-slate-800">
              {((application.delay_risk_score || 0) * 100).toFixed(0)}% Index
            </span>
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Statutory Action & Intake Review */}
        <div className="lg:col-span-2 space-y-6">
          {/* Statutory State Machine Action Desk */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center">
                <FileCheck className="w-4 h-4 mr-1.5 text-blue-700" />
                Statutory Decision & Transition Action Desk
              </h2>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-800 border border-blue-200">
                Guarded State Machine
              </span>
            </div>

            {actionError && (
              <div className="mt-3 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs">
                {actionError}
              </div>
            )}

            {actionSuccess && (
              <div className="mt-3 bg-emerald-50 border-l-4 border-emerald-500 p-3 rounded text-emerald-800 text-xs">
                {actionSuccess}
              </div>
            )}

            {permissible.length === 0 ? (
              <div className="mt-4 p-4 rounded bg-slate-50 border border-slate-200 text-center text-xs text-slate-600">
                This application docket is in a terminal or pending state ({application.current_status}). No further transitions permissible in this phase.
              </div>
            ) : (
              <form onSubmit={handleExecuteTransition} className="mt-4 space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Select Authorized Statutory Transition
                  </label>
                  <select
                    value={targetStatus}
                    onChange={(e) => setTargetStatus(e.target.value)}
                    required
                    className="w-full border border-slate-300 rounded-md p-2 bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-600 text-xs"
                  >
                    <option value="">Select statutory action...</option>
                    {permissible.map((p) => (
                      <option key={p.target} value={p.target}>
                        {p.label} (→ {p.target})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Official Statutory Remarks / Checklist Attestation
                  </label>
                  <textarea
                    rows={3}
                    value={transitionRemarks}
                    onChange={(e) => setTransitionRemarks(e.target.value)}
                    placeholder="Enter statutory basis under APH regulations, checklist results, or deficiency details..."
                    required
                    className="w-full border border-slate-300 rounded-md p-2 text-xs focus:outline-none focus:ring-1 focus:ring-blue-600"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    All remarks are permanently recorded in the immutable audit chain.
                  </p>
                </div>

                <div className="pt-2 flex justify-end">
                  <button
                    type="submit"
                    disabled={transitionMutation.isPending}
                    className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 disabled:opacity-50"
                  >
                    <Send className="w-3.5 h-3.5 mr-1.5" />
                    {transitionMutation.isPending
                      ? 'Executing Statutory Transition...'
                      : 'Record Statutory Transition'}
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* Intake Submission Parameters */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-3">
              Application Submission Parameters
            </h3>

            <div className="bg-slate-50 rounded border border-slate-200 p-4 font-mono text-xs overflow-x-auto text-slate-800">
              <pre>{JSON.stringify(submissionData, null, 2)}</pre>
            </div>
          </div>
        </div>

        {/* Right Column: AI Risk Indicators & Event Timeline */}
        <div className="space-y-6">
          {/* Explainable Delay Risk Indicators */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 text-amber-600" />
                Explainable Delay-Risk Factors
              </h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                Informational
              </span>
            </div>

            <div className="mt-3 space-y-2.5">
              {riskFactors.length === 0 ? (
                <p className="text-xs text-slate-500">No delay risk factors currently identified.</p>
              ) : (
                riskFactors.map((rf, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded border border-slate-200 bg-slate-50 text-xs"
                  >
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-800">{rf.factor}</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          rf.impact === 'HIGH'
                            ? 'bg-rose-100 text-rose-800'
                            : rf.impact === 'MEDIUM'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-slate-200 text-slate-700'
                        }`}
                      >
                        {rf.impact} IMPACT
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600 mt-1">{rf.detail}</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Immutable Statutory Timeline History */}
          <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-4 flex items-center">
              <History className="w-4 h-4 mr-1.5 text-blue-700" />
              Statutory Docket Timeline
            </h3>

            <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
              {application.events.map((ev) => (
                <div key={ev.id} className="relative text-xs">
                  <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-blue-600 ring-4 ring-white" />
                  <div>
                    <div className="font-bold text-slate-900">{ev.event_type}</div>
                    <div className="text-[11px] text-slate-500 font-mono">
                      {formatDate(ev.created_at)}
                    </div>
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
        </div>
      </div>
    </div>
  )
}
