import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { evcService } from '../services/evcService'
import { applicationService } from '../services/applicationService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import { EVCInspection } from '../types'
import {
  Users,
  Calendar,
  ShieldCheck,
  ShieldAlert,
  Plus,
  FileText,
  MapPin,
  CheckCircle2,
  Search,
  Award,
  Video,
} from 'lucide-react'

export const EVCPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isOfficer = user?.roles.some((r) => ['SUPER_ADMIN', 'REGIONAL_OFFICER'].includes(r.code))

  const [activeTab, setActiveTab] = useState<'inspections' | 'experts'>('inspections')

  // Search & Filters
  const [expertFilterType, setExpertFilterType] = useState<string>('')
  const [expertSearch, setExpertSearch] = useState<string>('')

  // Selected Inspection for Details/Panel
  const [selectedInspection, setSelectedInspection] = useState<EVCInspection | null>(null)

  // Schedule Modal
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false)
  const [schedAppId, setSchedAppId] = useState('')
  const [schedMode, setSchedMode] = useState('PHYSICAL')
  const [schedStartDate, setSchedStartDate] = useState('')
  const [schedEndDate, setSchedEndDate] = useState('')
  const [schedLink, setSchedLink] = useState('')
  const [schedCoords, setSchedCoords] = useState('')
  const [schedAddress, setSchedAddress] = useState('')
  const [scheduleError, setScheduleError] = useState<string | null>(null)

  // Assign Expert Modal
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false)
  const [selectedExpertId, setSelectedExpertId] = useState('')
  const [assignRole, setAssignRole] = useState('MEMBER')
  const [conflictResult, setConflictResult] = useState<any>(null)
  const [overrideConflict, setOverrideConflict] = useState(false)
  const [overrideJustification, setOverrideJustification] = useState('')
  const [assignError, setAssignError] = useState<string | null>(null)

  // Report Submission Modal
  const [isReportModalOpen, setIsReportModalOpen] = useState(false)
  const [overallRec, setOverallRec] = useState<'RECOMMENDED' | 'DEFICIENT' | 'SERIOUS_VIOLATIONS'>('RECOMMENDED')
  const [infraScore, setInfraScore] = useState(85.0)
  const [observations, setObservations] = useState('')
  const [deficienciesText, setDeficienciesText] = useState('')
  const [reportError, setReportError] = useState<string | null>(null)

  // Report Review Modal
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false)
  const [reviewVerdict, setReviewVerdict] = useState<'ACCEPTED' | 'RETURNED_FOR_CORRECTION'>('ACCEPTED')
  const [reviewRemarks, setReviewRemarks] = useState('')
  const [reviewError, setReviewError] = useState<string | null>(null)

  // Fetch Inspections
  const { data: inspections = [], isLoading: loadingInspections } = useQuery({
    queryKey: ['inspections'],
    queryFn: () => evcService.listInspections(),
  })

  // Fetch Experts
  const { data: experts = [], isLoading: loadingExperts } = useQuery({
    queryKey: ['experts', expertFilterType],
    queryFn: () => evcService.listExperts({ expert_type: expertFilterType || undefined }),
  })

  // Fetch Applications for Scheduling dropdown
  const { data: apps = [] } = useQuery({
    queryKey: ['applications-for-evc'],
    queryFn: () => applicationService.listApplications(),
  })

  // Schedule Mutation
  const scheduleMutation = useMutation({
    mutationFn: evcService.createInspection,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      setIsScheduleModalOpen(false)
      setScheduleError(null)
    },
    onError: (err: any) => {
      setScheduleError(err.message || 'Failed to schedule inspection')
    },
  })

  // Assign Expert Mutation
  const assignMutation = useMutation({
    mutationFn: (data: { inspId: string; payload: any }) =>
      evcService.assignExpert(data.inspId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      if (selectedInspection) {
        const updated = await evcService.getInspection(selectedInspection.id)
        setSelectedInspection(updated)
      }
      setIsAssignModalOpen(false)
      setSelectedExpertId('')
      setConflictResult(null)
      setAssignError(null)
    },
    onError: (err: any) => {
      setAssignError(err.message || 'Expert assignment failed')
    },
  })

  // Submit Report Mutation
  const reportMutation = useMutation({
    mutationFn: (data: { inspId: string; payload: any }) =>
      evcService.submitReport(data.inspId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      if (selectedInspection) {
        const updated = await evcService.getInspection(selectedInspection.id)
        setSelectedInspection(updated)
      }
      setIsReportModalOpen(false)
      setReportError(null)
    },
    onError: (err: any) => {
      setReportError(err.message || 'Failed to submit report')
    },
  })

  // Review Report Mutation
  const reviewMutation = useMutation({
    mutationFn: (data: { inspId: string; versionId: string; payload: any }) =>
      evcService.reviewReport(data.inspId, data.versionId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['inspections'] })
      if (selectedInspection) {
        const updated = await evcService.getInspection(selectedInspection.id)
        setSelectedInspection(updated)
      }
      setIsReviewModalOpen(false)
      setReviewError(null)
    },
    onError: (err: any) => {
      setReviewError(err.message || 'Failed to review report')
    },
  })

  // Handle live Conflict Check when expert is selected in Assign Modal
  const handleSelectExpert = async (expId: string) => {
    setSelectedExpertId(expId)
    setConflictResult(null)
    setAssignError(null)
    if (!expId || !selectedInspection) return

    try {
      const res = await evcService.checkExpertConflict(expId, selectedInspection.application_id)
      setConflictResult(res)
    } catch (err: any) {
      setAssignError(err.message)
    }
  }

  const filteredExperts = experts.filter((e) => {
    const matchesSearch =
      e.name.toLowerCase().includes(expertSearch.toLowerCase()) ||
      e.organization.toLowerCase().includes(expertSearch.toLowerCase()) ||
      e.district.toLowerCase().includes(expertSearch.toLowerCase())
    return matchesSearch
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center">
            <Users className="w-6 h-6 mr-2.5 text-blue-600" />
            Expert Visit Committee (EVC) Operations
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Independent Verification Panels, Automated Conflict-of-Interest Checks & Tamper-Evident Inspection Reports
          </p>
        </div>

        {isOfficer && activeTab === 'inspections' && (
          <button
            onClick={() => setIsScheduleModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Schedule EVC Inspection
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => {
              setActiveTab('inspections')
              setSelectedInspection(null)
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center ${
              activeTab === 'inspections'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Calendar className="w-4 h-4 mr-2" />
            Active Inspection Schedules ({inspections.length})
          </button>
          <button
            onClick={() => {
              setActiveTab('experts')
              setSelectedInspection(null)
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center ${
              activeTab === 'experts'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Award className="w-4 h-4 mr-2" />
            National Expert Roster ({experts.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Inspections */}
      {activeTab === 'inspections' && (
        <div className="space-y-6">
          {loadingInspections ? (
            <div className="p-8 text-center text-slate-500">Loading inspection schedules...</div>
          ) : inspections.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
              <Calendar className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <h3 className="text-base font-medium text-slate-900">No inspections scheduled</h3>
              <p className="text-sm text-slate-500 mt-1">
                Authorized regional officers may schedule an EVC inspection for an active application.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {inspections.map((insp) => (
                <div
                  key={insp.id}
                  className="bg-white border border-slate-200 rounded-lg p-5 hover:border-blue-300 transition-all shadow-sm"
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-3">
                        <span className="font-mono font-bold text-blue-700 text-base">
                          {insp.inspection_number}
                        </span>
                        <StatusBadge status={insp.status} />
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                          {insp.inspection_mode === 'VIRTUAL' ? (
                            <Video className="w-3 h-3 mr-1" />
                          ) : (
                            <MapPin className="w-3 h-3 mr-1" />
                          )}
                          {insp.inspection_mode}
                        </span>
                      </div>
                      <div className="text-sm text-slate-700 font-medium">
                        {insp.institution_name || 'Technical Institution'}
                      </div>
                      <div className="text-xs text-slate-500 flex items-center space-x-4">
                        <span>Dates: {formatDate(insp.scheduled_start_date)} — {formatDate(insp.scheduled_end_date)}</span>
                        {insp.location_address && <span>Location: {insp.location_address}</span>}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => setSelectedInspection(insp)}
                        className="px-3.5 py-1.5 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
                      >
                        Panel & Reports ({insp.panel_members.length})
                      </button>

                      {isOfficer && insp.status === 'SCHEDULED' && (
                        <button
                          onClick={async () => {
                            await evcService.transitionInspection(insp.id, 'IN_PROGRESS')
                            queryClient.invalidateQueries({ queryKey: ['inspections'] })
                          }}
                          className="px-3.5 py-1.5 bg-amber-600 text-white rounded-md text-sm font-medium hover:bg-amber-700"
                        >
                          Mark In Progress
                        </button>
                      )}

                      {isOfficer && ['SCHEDULED', 'IN_PROGRESS', 'RETURNED_FOR_CORRECTION'].includes(insp.status) && (
                        <button
                          onClick={() => {
                            setSelectedInspection(insp)
                            setIsReportModalOpen(true)
                          }}
                          className="px-3.5 py-1.5 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 flex items-center"
                        >
                          <FileText className="w-4 h-4 mr-1.5" />
                          Submit Report
                        </button>
                      )}

                      {isOfficer && insp.status === 'REPORT_SUBMITTED' && insp.latest_report && (
                        <button
                          onClick={() => {
                            setSelectedInspection(insp)
                            setIsReviewModalOpen(true)
                          }}
                          className="px-3.5 py-1.5 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 flex items-center"
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1.5" />
                          Review Report
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Panel Summary */}
                  {insp.panel_members.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap gap-2 items-center">
                      <span className="text-xs font-semibold text-slate-500 uppercase">Committee Panel:</span>
                      {insp.panel_members.map((pm) => (
                        <span
                          key={pm.id}
                          className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-800 border border-blue-200"
                        >
                          {pm.role === 'CHAIRPERSON' && <Award className="w-3 h-3 mr-1 text-blue-600" />}
                          {pm.expert_name} ({pm.role})
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Latest Report Verdict Banner */}
                  {insp.latest_report && (
                    <div className="mt-3 bg-slate-50 p-3 rounded border border-slate-200 text-xs flex justify-between items-center">
                      <div>
                        <span className="font-semibold text-slate-700">Latest Report v{insp.latest_report.version_number}:</span>{' '}
                        <span
                          className={`font-bold ${
                            insp.latest_report.overall_recommendation === 'RECOMMENDED'
                              ? 'text-emerald-700'
                              : 'text-rose-700'
                          }`}
                        >
                          {insp.latest_report.overall_recommendation}
                        </span>{' '}
                        (Infrastructure Score: {insp.latest_report.infrastructure_score}/100) —{' '}
                        <span className="text-slate-500 font-mono text-[11px]">
                          SHA256: {insp.latest_report.sha256_hash.substring(0, 16)}...
                        </span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-slate-600">Review:</span>
                        <StatusBadge status={insp.latest_report.review_status} />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Expert Pool */}
      {activeTab === 'experts' && (
        <div className="space-y-6">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row gap-4 justify-between bg-white p-4 rounded-lg border border-slate-200">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
              <input
                type="text"
                placeholder="Search experts by name, institution, or district..."
                value={expertSearch}
                onChange={(e) => setExpertSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div className="flex items-center space-x-3">
              <select
                value={expertFilterType}
                onChange={(e) => setExpertFilterType(e.target.value)}
                className="border border-slate-300 rounded-md py-2 px-3 text-sm focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">All Expertise Domains</option>
                <option value="ACADEMIC">Academic</option>
                <option value="INDUSTRY">Industry</option>
                <option value="REGULATORY">Regulatory</option>
              </select>
            </div>
          </div>

          {/* Expert Cards Grid */}
          {loadingExperts ? (
            <div className="p-8 text-center text-slate-500">Loading expert profiles...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredExperts.map((exp) => (
                <div key={exp.id} className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-base font-bold text-slate-900">{exp.name}</h4>
                      <p className="text-xs text-blue-700 font-medium">{exp.designation}</p>
                      <p className="text-xs text-slate-600">{exp.organization}</p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">
                      {exp.expert_type}
                    </span>
                  </div>

                  <div className="text-xs text-slate-500 space-y-1">
                    <div>
                      <span className="font-semibold text-slate-700">Qualifications:</span> {exp.qualifications} (Exp: {exp.experience_years} yrs)
                    </div>
                    <div>
                      <span className="font-semibold text-slate-700">Location:</span> {exp.district}, {exp.state} |{' '}
                      <span className="font-semibold text-slate-700">Alma Mater:</span> {exp.alma_mater}
                    </div>
                  </div>

                  {exp.specializations.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {exp.specializations.map((spec, i) => (
                        <span key={i} className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded text-[11px]">
                          {spec}
                        </span>
                      ))}
                    </div>
                  )}

                  {isOfficer && exp.conflict_declarations && exp.conflict_declarations.length > 0 && (
                    <div className="bg-amber-50 border border-amber-200 rounded p-2 text-xs text-amber-800">
                      <span className="font-bold flex items-center">
                        <ShieldAlert className="w-3.5 h-3.5 mr-1" />
                        Declared Conflicts ({exp.conflict_declarations.length}):
                      </span>
                      <ul className="list-disc list-inside mt-0.5 space-y-0.5 text-[11px]">
                        {exp.conflict_declarations.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Selected Inspection Panel Details Drawer / Modal */}
      {selectedInspection && !isReportModalOpen && !isReviewModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedInspection(null)}
          title={`EVC Docket: ${selectedInspection.inspection_number}`}
        >
          <div className="space-y-6">
            <div className="bg-slate-50 p-4 rounded border border-slate-200 space-y-2 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-700">Status:</span>
                <StatusBadge status={selectedInspection.status} />
              </div>
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Mode:</span>
                <span>{selectedInspection.inspection_mode}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Dates:</span>
                <span>{formatDate(selectedInspection.scheduled_start_date)} to {formatDate(selectedInspection.scheduled_end_date)}</span>
              </div>
              {selectedInspection.meeting_link && (
                <div className="flex justify-between">
                  <span className="font-bold text-slate-700">Virtual Meeting:</span>
                  <a href={selectedInspection.meeting_link} target="_blank" rel="noreferrer" className="text-blue-600 underline">
                    {selectedInspection.meeting_link}
                  </a>
                </div>
              )}
            </div>

            {/* Panel Members List */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h4 className="text-sm font-bold text-slate-900">Assigned Inspection Panel</h4>
                {isOfficer && ['SCHEDULED', 'DRAFT'].includes(selectedInspection.status) && (
                  <button
                    onClick={() => setIsAssignModalOpen(true)}
                    className="text-xs bg-blue-600 text-white px-2.5 py-1 rounded hover:bg-blue-700 font-medium"
                  >
                    + Add Panel Member
                  </button>
                )}
              </div>

              {selectedInspection.panel_members.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No experts assigned yet. Add members to constitute the panel.</p>
              ) : (
                <div className="space-y-2">
                  {selectedInspection.panel_members.map((pm) => (
                    <div key={pm.id} className="p-3 bg-white border border-slate-200 rounded text-xs space-y-1">
                      <div className="flex justify-between font-bold">
                        <span>{pm.expert_name} ({pm.role})</span>
                        <span className={pm.conflict_check_passed ? 'text-emerald-600' : 'text-rose-600'}>
                          {pm.conflict_check_passed ? '✓ COI Cleared' : '✗ Conflict'}
                        </span>
                      </div>
                      <div className="text-slate-600">{pm.expert_designation} — {pm.expert_organization}</div>
                      {pm.conflict_notes && (
                        <div className="text-amber-800 bg-amber-50 p-1.5 rounded text-[11px]">
                          <strong>Conflict Resolution:</strong> {pm.conflict_notes}
                        </div>
                      )}
                      <div className="text-slate-500 text-[11px] flex justify-between pt-1">
                        <span>Attendance: {pm.attendance_status}</span>
                        <span>Sign-off: {pm.sign_off_status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedInspection(null)}
                className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Schedule Inspection Modal */}
      <Modal
        isOpen={isScheduleModalOpen}
        onClose={() => setIsScheduleModalOpen(false)}
        title="Schedule Expert Visit Committee (EVC) Inspection"
      >
        <div className="space-y-4 text-sm">
          {scheduleError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {scheduleError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Application</label>
            <select
              value={schedAppId}
              onChange={(e) => setSchedAppId(e.target.value)}
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
              <label className="block text-xs font-semibold text-slate-700 mb-1">Inspection Mode</label>
              <select
                value={schedMode}
                onChange={(e) => setSchedMode(e.target.value)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              >
                <option value="PHYSICAL">Physical On-Site Visit</option>
                <option value="VIRTUAL">Virtual Inspection</option>
                <option value="HYBRID">Hybrid (Site + Remote)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Start Date & Time (UTC)</label>
              <input
                type="datetime-local"
                value={schedStartDate}
                onChange={(e) => setSchedStartDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">End Date & Time (UTC)</label>
            <input
              type="datetime-local"
              value={schedEndDate}
              onChange={(e) => setSchedEndDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          {schedMode !== 'PHYSICAL' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Video Meeting Link</label>
              <input
                type="url"
                placeholder="https://meet.aicte-india.org/..."
                value={schedLink}
                onChange={(e) => setSchedLink(e.target.value)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              />
            </div>
          )}

          {schedMode !== 'VIRTUAL' && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">GPS Coordinates (Lat, Long)</label>
                <input
                  type="text"
                  placeholder="28.5355, 77.3910"
                  value={schedCoords}
                  onChange={(e) => setSchedCoords(e.target.value)}
                  className="w-full border border-slate-300 rounded-md p-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Premises Address</label>
                <input
                  type="text"
                  placeholder="Main Campus, Sector 14..."
                  value={schedAddress}
                  onChange={(e) => setSchedAddress(e.target.value)}
                  className="w-full border border-slate-300 rounded-md p-2 text-sm"
                />
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsScheduleModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!schedAppId || !schedStartDate || !schedEndDate || scheduleMutation.isPending}
              onClick={() => {
                scheduleMutation.mutate({
                  application_id: schedAppId,
                  inspection_mode: schedMode,
                  scheduled_start_date: schedStartDate,
                  scheduled_end_date: schedEndDate,
                  meeting_link: schedLink || undefined,
                  location_coordinates: schedCoords || undefined,
                  location_address: schedAddress || undefined,
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {scheduleMutation.isPending ? 'Scheduling...' : 'Confirm Schedule'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Assign Expert Modal with Live Conflict-of-Interest Checker */}
      <Modal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        title="Assign Expert with Conflict-of-Interest Verification"
      >
        <div className="space-y-4 text-sm">
          {assignError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {assignError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Verified Expert</label>
            <select
              value={selectedExpertId}
              onChange={(e) => handleSelectExpert(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            >
              <option value="">Choose Expert from National Pool...</option>
              {experts.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.name} ({exp.designation}, {exp.district}, {exp.state})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Panel Role</label>
            <select
              value={assignRole}
              onChange={(e) => setAssignRole(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            >
              <option value="CHAIRPERSON">Committee Chairperson</option>
              <option value="MEMBER">Academic / Industry Member</option>
              <option value="CONVENER">Member Convener</option>
              <option value="SPECIALIST">Specialist Subject Matter Inspector</option>
            </select>
          </div>

          {/* Live Conflict Result Card */}
          {conflictResult && (
            <div
              className={`p-3 rounded border text-xs ${
                conflictResult.has_conflict
                  ? 'bg-rose-50 border-rose-200 text-rose-900'
                  : 'bg-emerald-50 border-emerald-200 text-emerald-900'
              }`}
            >
              <div className="font-bold flex items-center mb-1">
                {conflictResult.has_conflict ? (
                  <>
                    <ShieldAlert className="w-4 h-4 mr-1.5 text-rose-600" />
                    Statutory Conflict of Interest Detected ({conflictResult.policy_version})
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4 mr-1.5 text-emerald-600" />
                    Conflict Check Passed: Independent Expert Verified
                  </>
                )}
              </div>

              {conflictResult.has_conflict && (
                <div className="space-y-2 mt-2">
                  <ul className="list-disc list-inside text-[11px] text-rose-800 space-y-0.5">
                    {conflictResult.conflict_reasons.map((r: string, idx: number) => (
                      <li key={idx}>{r}</li>
                    ))}
                  </ul>

                  <div className="pt-2 border-t border-rose-200">
                    <label className="flex items-center text-xs font-semibold text-rose-900">
                      <input
                        type="checkbox"
                        checked={overrideConflict}
                        onChange={(e) => setOverrideConflict(e.target.checked)}
                        className="mr-2"
                      />
                      Statutory Reviewer Exemption Override
                    </label>

                    {overrideConflict && (
                      <div className="mt-2">
                        <textarea
                          placeholder="Mandatory documented justification (min 10 characters)..."
                          value={overrideJustification}
                          onChange={(e) => setOverrideJustification(e.target.value)}
                          className="w-full border border-rose-300 rounded p-1.5 text-xs bg-white text-slate-800"
                          rows={2}
                        />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsAssignModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={
                !selectedExpertId ||
                (conflictResult?.has_conflict && (!overrideConflict || overrideJustification.length < 10)) ||
                assignMutation.isPending
              }
              onClick={() => {
                if (!selectedInspection) return
                assignMutation.mutate({
                  inspId: selectedInspection.id,
                  payload: {
                    expert_id: selectedExpertId,
                    role: assignRole,
                    override_conflict: overrideConflict,
                    override_justification: overrideConflict ? overrideJustification : undefined,
                  },
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {assignMutation.isPending ? 'Assigning...' : 'Confirm Assignment'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Submit Inspection Report Modal */}
      <Modal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        title="Submit Structured EVC Inspection Report (SHA-256 Chained)"
      >
        <div className="space-y-4 text-sm">
          {reportError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {reportError}
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Overall Recommendation</label>
              <select
                value={overallRec}
                onChange={(e) => setOverallRec(e.target.value as any)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm font-bold"
              >
                <option value="RECOMMENDED">RECOMMENDED FOR APPROVAL</option>
                <option value="DEFICIENT">DEFICIENT (REQUIRES CORRECTION)</option>
                <option value="SERIOUS_VIOLATIONS">SERIOUS STATUTORY VIOLATIONS</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Infrastructure Score (0-100)</label>
              <input
                type="number"
                min="0"
                max="100"
                value={infraScore}
                onChange={(e) => setInfraScore(parseFloat(e.target.value))}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Key Observations & Findings</label>
            <textarea
              rows={4}
              value={observations}
              onChange={(e) => setObservations(e.target.value)}
              placeholder="Detailed statutory observations covering faculty, laboratories, master plan, and barrier-free access..."
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          {overallRec !== 'RECOMMENDED' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Identified Deficiencies</label>
              <textarea
                rows={2}
                value={deficienciesText}
                onChange={(e) => setDeficienciesText(e.target.value)}
                placeholder="Specific deficiencies requiring cure or compliance..."
                className="w-full border border-slate-300 rounded-md p-2 text-sm text-rose-700"
              />
            </div>
          )}

          <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
            <strong>Non-Repudiation Notice:</strong> Submitting this report will compute a cryptographic SHA-256 digest of the observations and store an immutable version record in the audit chain.
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsReportModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={observations.length < 10 || reportMutation.isPending}
              onClick={() => {
                if (!selectedInspection) return
                reportMutation.mutate({
                  inspId: selectedInspection.id,
                  payload: {
                    overall_recommendation: overallRec,
                    infrastructure_score: infraScore,
                    observations: observations,
                    deficiencies_identified: deficienciesText || undefined,
                    checklist_data: { overall_score: infraScore },
                  },
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {reportMutation.isPending ? 'Submitting...' : 'Sign & Submit Report'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Review Inspection Report Modal */}
      <Modal
        isOpen={isReviewModalOpen}
        onClose={() => setIsReviewModalOpen(false)}
        title="Statutory Review of Submitted EVC Report"
      >
        <div className="space-y-4 text-sm">
          {reviewError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {reviewError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Review Decision</label>
            <select
              value={reviewVerdict}
              onChange={(e) => setReviewVerdict(e.target.value as any)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm font-bold"
            >
              <option value="ACCEPTED">ACCEPT REPORT IN FULL</option>
              <option value="RETURNED_FOR_CORRECTION">RETURN FOR CORRECTION / RE-VERIFICATION</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Review Remarks & Statutory Directives</label>
            <textarea
              rows={3}
              value={reviewRemarks}
              onChange={(e) => setReviewRemarks(e.target.value)}
              placeholder="State regulatory findings and reasons for acceptance or return..."
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsReviewModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={reviewRemarks.length < 5 || reviewMutation.isPending}
              onClick={() => {
                if (!selectedInspection || !selectedInspection.latest_report) return
                reviewMutation.mutate({
                  inspId: selectedInspection.id,
                  versionId: selectedInspection.latest_report.id,
                  payload: {
                    review_status: reviewVerdict,
                    review_remarks: reviewRemarks,
                  },
                })
              }}
              className="px-4 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {reviewMutation.isPending ? 'Saving...' : 'Finalize Review'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
