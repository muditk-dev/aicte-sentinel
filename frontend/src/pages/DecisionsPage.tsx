import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { decisionService } from '../services/decisionService'
import { applicationService } from '../services/applicationService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import { StatutoryDecision } from '../types'
import {
  Award,
  ShieldCheck,
  Plus,
  FileCheck,
  Scale,
  RefreshCw,
} from 'lucide-react'

export const DecisionsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isAuthorizedOfficer = user?.roles.some((r) => ['SUPER_ADMIN', 'REGIONAL_OFFICER'].includes(r.code))

  const [selectedDecision, setSelectedDecision] = useState<StatutoryDecision | null>(null)

  // Issue Decision Modal State
  const [isIssueModalOpen, setIsIssueModalOpen] = useState(false)
  const [targetAppId, setTargetAppId] = useState('')
  const [decisionType, setDecisionType] = useState<string>('APPROVED')
  const [approvedIntake, setApprovedIntake] = useState<number>(360)
  const [reasons, setReasons] = useState('')
  const [declaration, setDeclaration] = useState(
    `I, ${user?.full_name || 'Statutory Officer'}, ${user?.designation || 'Authorized Signatory'}, hereby certify and formally attest that this decision has been rendered following verified scrutiny, applicable inspection reports, and committee proceedings in full accordance with the AICTE Act 1987 and Approval Process Handbook 2026-27 regulations.`
  )
  const [conditions, setConditions] = useState<Array<{ condition_code: string; description: string; due_date: string }>>([
    { condition_code: 'COND-FIRE-SAFETY', description: 'Submit certified fire safety NOC within 60 days.', due_date: '2026-12-31' },
  ])
  const [issueError, setIssueError] = useState<string | null>(null)

  // Reconsideration Modal State
  const [isReconsiderModalOpen, setIsReconsiderModalOpen] = useState(false)
  const [reconsiderPetition, setReconsiderPetition] = useState('')
  const [reconsiderReason, setReconsiderReason] = useState('')
  const [reconsiderError, setReconsiderError] = useState<string | null>(null)

  // Fetch Finalized Decisions
  const { data: decisions = [], isLoading: loadingDecisions } = useQuery({
    queryKey: ['statutory-decisions'],
    queryFn: () => decisionService.listDecisions(),
  })

  // Fetch Applications eligible for decision
  const { data: apps = [] } = useQuery({
    queryKey: ['applications-for-decision'],
    queryFn: () => applicationService.listApplications(),
  })

  // Issue Decision Mutation
  const issueMutation = useMutation({
    mutationFn: decisionService.issueDecision,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statutory-decisions'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsIssueModalOpen(false)
      setIssueError(null)
    },
    onError: (err: any) => {
      setIssueError(err.message || 'Failed to issue statutory decision')
    },
  })

  // Reconsideration Mutation
  const reconsiderMutation = useMutation({
    mutationFn: (data: { id: string; payload: any }) =>
      decisionService.requestReconsideration(data.id, data.payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['statutory-decisions'] })
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsReconsiderModalOpen(false)
      setReconsiderError(null)
    },
    onError: (err: any) => {
      setReconsiderError(err.message || 'Failed to docket reconsideration')
    },
  })

  const addCondition = () => {
    setConditions([
      ...conditions,
      { condition_code: `COND-${Date.now().toString().slice(-4)}`, description: '', due_date: '' },
    ])
  }

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center">
            <Award className="w-6 h-6 mr-2.5 text-blue-600" />
            Statutory Decision Authorization Desk
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Official Executive Approval, Conditional Sanction, and Rejection Determinations with Non-Repudiation Attestation
          </p>
        </div>

        {isAuthorizedOfficer && (
          <button
            onClick={() => setIsIssueModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Issue Statutory Decision
          </button>
        )}
      </div>

      {/* Decisions Registry List */}
      <div className="space-y-4">
        {loadingDecisions ? (
          <div className="p-8 text-center text-slate-500">Loading statutory decisions...</div>
        ) : decisions.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
            <Award className="w-12 h-12 mx-auto text-slate-300 mb-3" />
            <h3 className="text-base font-medium text-slate-900">No finalized decisions rendered yet</h3>
            <p className="text-sm text-slate-500 mt-1">
              Authorized Regional Officers or Central Council members can render formal statutory decisions once scrutiny and inspection prerequisites are fulfilled.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {decisions.map((dec) => (
              <div
                key={dec.id}
                className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm hover:border-blue-300 transition-all space-y-4"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-3">
                      <span className="font-mono font-bold text-blue-800 text-base">
                        {dec.decision_number}
                      </span>
                      <StatusBadge status={dec.decision_type} />
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                        AY {dec.academic_year}
                      </span>
                      {dec.is_reconsidered && (
                        <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800 flex items-center">
                          <Scale className="w-3 h-3 mr-1" />
                          Appellate Reconsideration Docketed
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-bold text-slate-900">
                      {dec.institution_name} ({dec.application_number})
                    </div>
                    <div className="text-xs text-slate-500 flex items-center space-x-4">
                      <span>Authorized By: <strong>{dec.authorized_by_name}</strong> ({dec.authority_role})</span>
                      <span>Authorized At: {formatDate(dec.authorized_at)}</span>
                      {dec.intake_approved && <span>Approved Intake: <strong>{dec.intake_approved} Seats</strong></span>}
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => setSelectedDecision(dec)}
                      className="px-3.5 py-1.5 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 flex items-center"
                    >
                      <FileCheck className="w-4 h-4 mr-1.5" />
                      View Certificate
                    </button>

                    {isAuthorizedOfficer && !dec.is_reconsidered && ['REJECTED', 'CONDITIONALLY_APPROVED'].includes(dec.decision_type) && (
                      <button
                        onClick={() => {
                          setSelectedDecision(dec)
                          setIsReconsiderModalOpen(true)
                        }}
                        className="px-3.5 py-1.5 border border-amber-300 bg-amber-50 text-amber-800 rounded-md text-sm font-medium hover:bg-amber-100 flex items-center"
                      >
                        <RefreshCw className="w-4 h-4 mr-1.5" />
                        Docket for SAC Review
                      </button>
                    )}
                  </div>
                </div>

                {/* Reasons excerpt */}
                <div className="text-xs text-slate-700 bg-slate-50 p-3 rounded border border-slate-200">
                  <span className="font-bold">Statutory Ground:</span> {dec.reasons}
                </div>

                {/* Conditions list if conditional */}
                {dec.conditions && dec.conditions.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Statutory Compliance Conditions ({dec.conditions.length}):
                    </span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {dec.conditions.map((cond) => (
                        <div key={cond.id} className="p-2.5 bg-amber-50 border border-amber-200 rounded text-xs">
                          <div className="font-bold text-amber-900 flex justify-between">
                            <span>{cond.condition_code}</span>
                            <span className="text-[11px] font-semibold text-amber-700">Due: {formatDate(cond.due_date)}</span>
                          </div>
                          <p className="text-amber-800 mt-0.5 text-[11px]">{cond.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cryptographic Attestation Stamp */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-100 gap-2">
                  <div className="flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    <span className="font-mono truncate max-w-md">SHA-256 Non-Repudiation Attestation: {dec.sha256_attestation}</span>
                  </div>
                  <span className="font-medium text-slate-600">APH Policy: {dec.governing_policy_version}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Decision Certificate Modal */}
      {selectedDecision && !isReconsiderModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedDecision(null)}
          title="Official AICTE Statutory Decision Certificate"
        >
          <div className="space-y-6 text-sm">
            {/* National Emblem & Title Header */}
            <div className="text-center pb-4 border-b border-slate-200">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-600">
                All India Council for Technical Education
              </div>
              <div className="text-lg font-bold text-slate-900 mt-1">
                Statutory Regulatory Determination
              </div>
              <div className="text-xs text-slate-500">
                Issued under the AICTE Act 1987 & APH 2026-27 Regulations
              </div>
            </div>

            {/* Certificate Details Grid */}
            <div className="grid grid-cols-2 gap-3 bg-slate-50 p-4 rounded border border-slate-200 text-xs">
              <div>
                <span className="font-bold text-slate-500">Decision Number:</span>
                <p className="font-mono font-bold text-slate-900">{selectedDecision.decision_number}</p>
              </div>
              <div>
                <span className="font-bold text-slate-500">Statutory Verdict:</span>
                <p className="font-bold text-blue-700">{selectedDecision.decision_type}</p>
              </div>
              <div>
                <span className="font-bold text-slate-500">Technical Institution:</span>
                <p className="font-medium text-slate-900">{selectedDecision.institution_name}</p>
              </div>
              <div>
                <span className="font-bold text-slate-500">Application Number:</span>
                <p className="font-mono text-slate-800">{selectedDecision.application_number}</p>
              </div>
              <div>
                <span className="font-bold text-slate-500">Academic Year:</span>
                <p className="font-medium text-slate-900">{selectedDecision.academic_year}</p>
              </div>
              <div>
                <span className="font-bold text-slate-500">Sanctioned Intake:</span>
                <p className="font-bold text-slate-900">{selectedDecision.intake_approved || 'N/A'} Seats</p>
              </div>
            </div>

            {/* Findings & Reasons */}
            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-700">Official Statutory Findings & Reasons:</span>
              <p className="p-3 bg-white border border-slate-200 rounded text-slate-800 leading-relaxed">
                {selectedDecision.reasons}
              </p>
            </div>

            {/* Conditions if any */}
            {selectedDecision.conditions.length > 0 && (
              <div className="space-y-2 text-xs">
                <span className="font-bold text-amber-800">Mandatory Compliance Conditions:</span>
                <div className="space-y-1.5">
                  {selectedDecision.conditions.map((c) => (
                    <div key={c.id} className="p-2 bg-amber-50 border border-amber-200 rounded">
                      <div className="flex justify-between font-bold text-amber-900">
                        <span>{c.condition_code}</span>
                        <span>Due: {formatDate(c.due_date)}</span>
                      </div>
                      <p className="text-amber-800 text-[11px] mt-0.5">{c.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Human Officer Attestation Declaration */}
            <div className="p-3 bg-blue-50 border border-blue-200 rounded text-xs text-blue-900 space-y-1">
              <div className="font-bold flex items-center">
                <ShieldCheck className="w-4 h-4 mr-1 text-blue-700" />
                Authorized Human Signatory Attestation
              </div>
              <p className="text-[11px] leading-relaxed italic">{selectedDecision.declaration_text}</p>
              <div className="pt-2 flex justify-between items-center text-[11px] font-semibold text-blue-800 border-t border-blue-200">
                <span>Signatory: {selectedDecision.authorized_by_name} ({selectedDecision.authority_role})</span>
                <span>Date: {formatDate(selectedDecision.authorized_at)}</span>
              </div>
            </div>

            {/* Cryptographic Hash */}
            <div className="p-2 bg-slate-100 rounded text-center font-mono text-[11px] text-slate-600 break-all">
              Attestation SHA-256 Digest: {selectedDecision.sha256_attestation}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedDecision(null)}
                className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Close Certificate
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Issue Decision Modal */}
      <Modal
        isOpen={isIssueModalOpen}
        onClose={() => setIsIssueModalOpen(false)}
        title="Render Consequential Statutory Determination"
      >
        <div className="space-y-4 text-sm">
          {issueError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {issueError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Application</label>
            <select
              value={targetAppId}
              onChange={(e) => setTargetAppId(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            >
              <option value="">Select an Application...</option>
              {apps.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.application_number} ({app.current_status})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Statutory Determination Type</label>
              <select
                value={decisionType}
                onChange={(e) => setDecisionType(e.target.value)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm font-bold"
              >
                <option value="APPROVED">STATUTORY APPROVAL</option>
                <option value="CONDITIONALLY_APPROVED">CONDITIONAL APPROVAL</option>
                <option value="REJECTED">STATUTORY REJECTION</option>
                <option value="RETURNED_FOR_REVIEW">RETURN FOR SCRUTINY REVIEW</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Approved Student Intake</label>
              <input
                type="number"
                min="0"
                value={approvedIntake}
                onChange={(e) => setApprovedIntake(parseInt(e.target.value) || 0)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Statutory Reasons & Grounding</label>
            <textarea
              rows={3}
              placeholder="State regulatory justification, referenced APH clauses, and inspection verdicts..."
              value={reasons}
              onChange={(e) => setReasons(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          {/* Conditional Approval Conditions Generator */}
          {decisionType === 'CONDITIONALLY_APPROVED' && (
            <div className="space-y-2 p-3 bg-amber-50 rounded border border-amber-200">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-amber-900">Mandatory Conditions (At least 1 required)</span>
                <button
                  type="button"
                  onClick={addCondition}
                  className="text-xs bg-amber-600 text-white px-2 py-0.5 rounded hover:bg-amber-700"
                >
                  + Add Condition
                </button>
              </div>

              {conditions.map((cond, idx) => (
                <div key={idx} className="space-y-2 p-2 bg-white rounded border border-amber-200 text-xs">
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      placeholder="Condition Code (e.g. COND-FIRE-NOC)"
                      value={cond.condition_code}
                      onChange={(e) => {
                        const copy = [...conditions]
                        copy[idx].condition_code = e.target.value
                        setConditions(copy)
                      }}
                      className="border border-slate-300 rounded p-1 text-xs"
                    />
                    <input
                      type="date"
                      value={cond.due_date}
                      onChange={(e) => {
                        const copy = [...conditions]
                        copy[idx].due_date = e.target.value
                        setConditions(copy)
                      }}
                      className="border border-slate-300 rounded p-1 text-xs"
                    />
                  </div>
                  <div className="flex space-x-2">
                    <input
                      type="text"
                      placeholder="Condition Description..."
                      value={cond.description}
                      onChange={(e) => {
                        const copy = [...conditions]
                        copy[idx].description = e.target.value
                        setConditions(copy)
                      }}
                      className="flex-1 border border-slate-300 rounded p-1 text-xs"
                    />
                    {conditions.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeCondition(idx)}
                        className="text-rose-600 hover:text-rose-800 text-xs font-bold px-1"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Non-Repudiation Human Officer Declaration */}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Human Attestation & Statutory Oath Declaration
            </label>
            <textarea
              rows={3}
              value={declaration}
              onChange={(e) => setDeclaration(e.target.value)}
              className="w-full border border-blue-300 bg-blue-50/50 rounded-md p-2 text-xs text-slate-800 font-mono"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsIssueModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={
                !targetAppId ||
                reasons.length < 15 ||
                declaration.length < 20 ||
                (decisionType === 'CONDITIONALLY_APPROVED' && conditions.length === 0) ||
                issueMutation.isPending
              }
              onClick={() => {
                issueMutation.mutate({
                  application_id: targetAppId,
                  decision_type: decisionType,
                  reasons: reasons,
                  evidence_references: ['STATUTORY_SCRUTINY_PASS', 'EVC_RECOMMENDED'],
                  intake_approved: approvedIntake,
                  valid_for_years: 1,
                  conditions: decisionType === 'CONDITIONALLY_APPROVED' ? conditions : [],
                  declaration_attestation: declaration,
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {issueMutation.isPending ? 'Issuing Decision...' : 'Formally Issue Decision'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Appellate Reconsideration Modal */}
      <Modal
        isOpen={isReconsiderModalOpen}
        onClose={() => setIsReconsiderModalOpen(false)}
        title="Docket for Standing Appellate Committee (SAC) Review"
      >
        <div className="space-y-4 text-sm">
          {reconsiderError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {reconsiderError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Appellate Petition Reference</label>
            <input
              type="text"
              placeholder="SAC-PETITION-2026-..."
              value={reconsiderPetition}
              onChange={(e) => setReconsiderPetition(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Legal Grounds for Reconsideration</label>
            <textarea
              rows={3}
              placeholder="State grounds on why the rejected or conditional verdict should be reviewed by the Apex Appellate Committee..."
              value={reconsiderReason}
              onChange={(e) => setReconsiderReason(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsReconsiderModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!reconsiderPetition || reconsiderReason.length < 20 || reconsiderMutation.isPending}
              onClick={() => {
                if (!selectedDecision) return
                reconsiderMutation.mutate({
                  id: selectedDecision.id,
                  payload: {
                    appeal_petition_reference: reconsiderPetition,
                    appeal_reason: reconsiderReason,
                  },
                })
              }}
              className="px-4 py-2 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
            >
              {reconsiderMutation.isPending ? 'Docketing...' : 'Confirm Appellate Review'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
