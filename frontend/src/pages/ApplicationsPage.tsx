import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { applicationService } from '../services/applicationService'
import { workflowService } from '../services/workflowService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import {
  Plus,
  Search,
  Filter,
  AlertCircle,
} from 'lucide-react'

export const ApplicationsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Intake Form State
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [academicYear, setAcademicYear] = useState('2026-2027')
  const [intakeCapacity, setIntakeCapacity] = useState('360')
  const [primaryDiscipline, setPrimaryDiscipline] = useState('Computer Science & Engineering')
  const [modalError, setModalError] = useState<string | null>(null)

  const { data: applications = [], isLoading } = useQuery({
    queryKey: ['applications', statusFilter],
    queryFn: () => applicationService.listApplications(statusFilter || undefined),
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['workflow-templates'],
    queryFn: () => workflowService.listTemplates(),
  })

  const createMutation = useMutation({
    mutationFn: applicationService.createApplication,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['applications'] })
      setIsModalOpen(false)
      setSelectedTemplateId('')
    },
    onError: (err: any) => {
      setModalError(err.message || 'Failed to submit application docket.')
    },
  })

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setModalError(null)

    if (!selectedTemplateId) {
      setModalError('Please select a statutory workflow category.')
      return
    }

    createMutation.mutate({
      template_id: selectedTemplateId,
      academic_year: academicYear,
      submission_data: {
        intake_capacity: Number(intakeCapacity),
        primary_discipline: primaryDiscipline,
        submission_timestamp: new Date().toISOString(),
      },
    })
  }

  const filteredApps = applications.filter((app) =>
    app.application_number.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const isInstitutionAdmin = user?.roles.some((r) => r.code === 'INSTITUTION_ADMIN')

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Statutory Applications Registry
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Complete institutional application lifecycle governed by AICTE Approval Process Handbook (APH)
          </p>
        </div>

        {isInstitutionAdmin && (
          <button
            onClick={() => {
              setModalError(null)
              setIsModalOpen(true)
            }}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800 transition-colors"
          >
            <Plus className="w-4 h-4 mr-1.5" />
            Initiate New Application
          </button>
        )}
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="h-4 w-4" />
          </div>
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by Docket Number..."
            className="block w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600"
          />
        </div>

        <div className="flex items-center space-x-2 w-full md:w-auto">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">State:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-md py-1.5 px-3 bg-white text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600"
          >
            <option value="">All Statutory States</option>
            <option value="DRAFT">Draft</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_SCRUTINY">Under Scrutiny</option>
            <option value="DEFICIENCY_ISSUED">Deficiency Issued</option>
            <option value="RESUBMITTED">Resubmitted</option>
            <option value="EVC_SCHEDULED">EVC Scheduled</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-100 text-slate-600 font-bold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3">Docket Number</th>
                <th className="px-6 py-3">Academic Cycle</th>
                <th className="px-6 py-3">Statutory State</th>
                <th className="px-6 py-3">SLA Status</th>
                <th className="px-6 py-3">Created Date</th>
                <th className="px-6 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    Loading dockets...
                  </td>
                </tr>
              ) : filteredApps.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">
                    No matching application dockets found.
                  </td>
                </tr>
              ) : (
                filteredApps.map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 font-mono font-bold text-blue-700">
                      {app.application_number}
                    </td>
                    <td className="px-6 py-4 text-slate-700">{app.academic_year}</td>
                    <td className="px-6 py-4">
                      <StatusBadge status={app.current_status} />
                    </td>
                    <td className="px-6 py-4 text-slate-600">
                      {app.sla_deadline ? (
                        <span className="text-[11px] text-slate-500 font-mono">
                          Target: {app.sla_deadline.split('T')[0]}
                        </span>
                      ) : (
                        <span className="text-slate-400">Within statutory SLA</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-slate-500 font-mono text-[11px]">
                      {formatDate(app.created_at)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/applications/${app.id}`}
                        className="inline-flex items-center px-2.5 py-1 text-xs font-semibold rounded text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100"
                      >
                        Inspect Docket →
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Application Intake Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Initiate Statutory Application Docket"
      >
        {modalError && (
          <div className="mb-4 bg-rose-50 border-l-4 border-rose-500 p-3 rounded text-rose-800 text-xs flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{modalError}</span>
          </div>
        )}

        <form onSubmit={handleCreateSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Statutory Workflow Template
            </label>
            <select
              value={selectedTemplateId}
              onChange={(e) => setSelectedTemplateId(e.target.value)}
              required
              className="w-full border border-slate-300 rounded-md p-2 bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-600 text-xs"
            >
              <option value="">Select approval handbook chapter...</option>
              {templates.map((tmpl) => (
                <option key={tmpl.id} value={tmpl.id}>
                  {tmpl.name} ({tmpl.category})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Academic Year
            </label>
            <input
              type="text"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-xs"
              required
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Primary Program / Discipline
            </label>
            <input
              type="text"
              value={primaryDiscipline}
              onChange={(e) => setPrimaryDiscipline(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-xs"
              required
            />
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider mb-1">
              Proposed Intake Capacity (Seats)
            </label>
            <input
              type="number"
              value={intakeCapacity}
              onChange={(e) => setIntakeCapacity(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-xs"
              required
            />
          </div>

          <div className="pt-3 border-t border-slate-200 flex justify-end space-x-2">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-3 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 rounded text-white bg-blue-700 hover:bg-blue-800 font-semibold shadow-sm disabled:opacity-50"
            >
              {createMutation.isPending ? 'Initializing Docket...' : 'Create Application Draft'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
