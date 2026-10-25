import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { complianceService } from '../services/complianceService'
import { institutionService } from '../services/institutionService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import {
  FileText,
  Search,
  Plus,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  Building,
} from 'lucide-react'

export const ObligationsRegisterPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isOfficerOrAdmin = user?.roles.some((r) =>
    ['SUPER_ADMIN', 'ADMIN', 'REGIONAL_OFFICER', 'SCRUTINY_OFFICER'].includes(r.code)
  )

  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false)

  // Create Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [targetInstitutionId, setTargetInstitutionId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('FACULTY_RATIO')
  const [sourceReference, setSourceReference] = useState('APH 2026-27 Clause 4.1.1')
  const [dueDate, setDueDate] = useState('')
  const [recurrence, setRecurrence] = useState('ANNUAL')
  const [createError, setCreateError] = useState<string | null>(null)

  // Fetch Obligations
  const { data: obligations = [], isLoading, refetch } = useQuery({
    queryKey: ['compliance-obligations', categoryFilter, statusFilter, searchQuery, overdueOnly],
    queryFn: () =>
      complianceService.listObligations({
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
        search: searchQuery || undefined,
        overdue_only: overdueOnly || undefined,
      }),
  })

  // Fetch Institutions for create modal
  const { data: institutions = [] } = useQuery({
    queryKey: ['institutions-list'],
    queryFn: () => institutionService.listInstitutions(),
    enabled: isOfficerOrAdmin && isCreateModalOpen,
  })

  // Create Mutation
  const createMutation = useMutation({
    mutationFn: complianceService.createObligation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-obligations'] })
      queryClient.invalidateQueries({ queryKey: ['compliance-summary'] })
      setIsCreateModalOpen(false)
      setTitle('')
      setDescription('')
      setDueDate('')
      setCreateError(null)
    },
    onError: (err: any) => {
      setCreateError(err.message || 'Failed to create compliance obligation')
    },
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    if (!targetInstitutionId || !title || !description || !dueDate) {
      setCreateError('Please complete all required fields.')
      return
    }

    createMutation.mutate({
      institution_id: targetInstitutionId,
      title,
      description,
      category,
      source_reference: sourceReference,
      applicability: 'ALL_TECHNICAL_INSTITUTIONS',
      issue_date: new Date().toISOString(),
      due_date: new Date(dueDate).toISOString(),
      recurrence,
      is_synthetic_demonstration: false,
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center">
            <FileText className="w-6 h-6 mr-2 text-blue-700" />
            Statutory Obligations Register
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Official post-approval mandatory compliance requirements, verifications, and submissions
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {isOfficerOrAdmin && (
            <button
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-white bg-blue-700 rounded hover:bg-blue-800 shadow-sm transition-colors"
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              Issue New Obligation
            </button>
          )}

          <button
            onClick={() => refetch()}
            className="p-1.5 text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded shadow-sm"
            title="Refresh list"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm flex flex-col md:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by obligation code, title, or statutory clause..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Categories</option>
            <option value="FACULTY_RATIO">Faculty Ratio (FSR)</option>
            <option value="SAFETY_CLEARANCE">Safety & Fire NOC</option>
            <option value="INFRASTRUCTURE">Infrastructure Norms</option>
            <option value="AFFILIATION">University Affiliation</option>
            <option value="FINANCIAL_DISCLOSURE">Financial & FDR</option>
            <option value="ANNUAL_REPORT">Annual Disclosures</option>
            <option value="GENERAL">General Regulatory</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 border border-slate-300 rounded bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="PENDING">Pending Action</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="COMPLIANT">Compliant</option>
            <option value="DEFICIENT">Deficient</option>
            <option value="OVERDUE">Overdue</option>
            <option value="CLOSED">Closed</option>
          </select>

          <label className="flex items-center space-x-1.5 cursor-pointer text-slate-700 font-medium px-2 py-1 rounded bg-slate-50 border border-slate-200">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded text-red-600 focus:ring-0"
            />
            <span className="text-red-700">Overdue Only</span>
          </label>
        </div>
      </div>

      {/* Obligations Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-slate-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-600" />
            Loading obligations register...
          </div>
        ) : obligations.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <h3 className="text-sm font-bold text-slate-800">No Compliance Obligations Found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              No statutory obligations match the selected search and filter criteria.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-xs">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Obligation Code & Title</th>
                  <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Institution</th>
                  <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Category</th>
                  <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Statutory Source</th>
                  <th className="px-4 py-2.5 text-left font-bold text-slate-700 uppercase tracking-wider">Due Date</th>
                  <th className="px-4 py-2.5 text-center font-bold text-slate-700 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-2.5 text-right font-bold text-slate-700 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {obligations.map((ob) => {
                  const isPastDue = new Date(ob.due_date) < new Date() && ob.status !== 'COMPLIANT' && ob.status !== 'CLOSED'
                  return (
                    <tr key={ob.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-mono text-[11px] font-bold text-blue-800 flex items-center space-x-1.5">
                          <span>{ob.obligation_code}</span>
                          {ob.is_synthetic_demonstration && (
                            <span className="text-[9px] px-1.5 py-0.2 bg-amber-100 text-amber-800 rounded font-sans font-semibold">
                              DEMO
                            </span>
                          )}
                        </div>
                        <div className="font-semibold text-slate-900 mt-0.5 max-w-md">{ob.title}</div>
                      </td>

                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-800 flex items-center">
                          <Building className="w-3.5 h-3.5 mr-1 text-slate-400" />
                          {ob.institution_name || 'Assigned Institution'}
                        </div>
                        <span className="text-[10px] text-slate-400 block mt-0.5">{ob.applicability}</span>
                      </td>

                      <td className="px-4 py-3">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[11px]">
                          {ob.category.replace('_', ' ')}
                        </span>
                        <span className="text-[10px] text-slate-400 block mt-1">{ob.recurrence}</span>
                      </td>

                      <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">
                        {ob.source_reference}
                      </td>

                      <td className="px-4 py-3">
                        <div className={`font-mono text-[11px] font-semibold ${isPastDue ? 'text-red-700 font-bold' : 'text-slate-800'}`}>
                          {formatDate(ob.due_date)}
                        </div>
                        {isPastDue && (
                          <span className="text-[10px] font-bold text-red-600 flex items-center mt-0.5">
                            <AlertTriangle className="w-3 h-3 mr-0.5" />
                            Overdue
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3 text-center">
                        <StatusBadge status={ob.status} />
                      </td>

                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/compliance/obligations/${ob.id}`}
                          className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded border border-blue-200 transition-colors"
                        >
                          Review
                          <ExternalLink className="w-3 h-3 ml-1" />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Obligation Modal */}
      {isCreateModalOpen && (
        <Modal
          isOpen={isCreateModalOpen}
          onClose={() => setIsCreateModalOpen(false)}
          title="Issue Post-Approval Compliance Obligation"
        >
          <form onSubmit={handleCreate} className="space-y-4 text-xs">
            {createError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-700 rounded text-xs flex items-center">
                <AlertTriangle className="w-4 h-4 mr-1.5 flex-shrink-0" />
                {createError}
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-bold mb-1">Target Institution *</label>
              <select
                value={targetInstitutionId}
                onChange={(e) => setTargetInstitutionId(e.target.value)}
                required
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs"
              >
                <option value="">Select Institution</option>
                {institutions.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({i.code}) — {i.region}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">Obligation Title *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Annual Faculty-Student Ratio (FSR) Mandatory Compliance Disclosure"
                required
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">Description & Mandatory Proofs *</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                placeholder="Detail the exact statutory verification requirements and documents to be uploaded..."
                required
                className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Category *</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs"
                >
                  <option value="FACULTY_RATIO">Faculty Ratio (FSR)</option>
                  <option value="SAFETY_CLEARANCE">Safety Clearance & Fire NOC</option>
                  <option value="INFRASTRUCTURE">Infrastructure Norms</option>
                  <option value="AFFILIATION">University Affiliation</option>
                  <option value="FINANCIAL_DISCLOSURE">Financial & FDR</option>
                  <option value="ANNUAL_REPORT">Annual Disclosures</option>
                  <option value="GENERAL">General Regulatory</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Recurrence *</label>
                <select
                  value={recurrence}
                  onChange={(e) => setRecurrence(e.target.value)}
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded bg-white text-xs"
                >
                  <option value="ONE_TIME">One Time</option>
                  <option value="ANNUAL">Annual</option>
                  <option value="BIENNIAL">Biennial (2 Years)</option>
                  <option value="QUARTERLY">Quarterly</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Statutory Clause Reference *</label>
                <input
                  type="text"
                  value={sourceReference}
                  onChange={(e) => setSourceReference(e.target.value)}
                  placeholder="e.g. APH 2026-27 Clause 4.1.1"
                  required
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Due Date *</label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                  required
                  className="w-full px-2.5 py-1.5 border border-slate-300 rounded text-xs"
                />
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 rounded disabled:opacity-50"
              >
                {createMutation.isPending ? 'Issuing...' : 'Issue Obligation'}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
