import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { committeeService } from '../services/committeeService'
import { applicationService } from '../services/applicationService'
import { authService } from '../services/authService'
import { StatusBadge } from '../components/StatusBadge'
import { Modal } from '../components/Modal'
import { formatDate } from '../lib/utils'
import { Hearing } from '../types'
import {
  Scale,
  Calendar,
  Plus,
  FileText,
  Landmark,
  UserCheck,
} from 'lucide-react'

export const CommitteesPage: React.FC = () => {
  const queryClient = useQueryClient()
  const user = authService.getCurrentUser()
  const isOfficer = user?.roles.some((r) => ['SUPER_ADMIN', 'REGIONAL_OFFICER'].includes(r.code))

  const [activeTab, setActiveTab] = useState<'hearings' | 'benches'>('hearings')
  const [selectedHearing, setSelectedHearing] = useState<Hearing | null>(null)

  // Schedule Hearing Modal
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false)
  const [schedCommitteeId, setSchedCommitteeId] = useState('')
  const [schedType, setSchedType] = useState('SHC')
  const [schedDate, setSchedDate] = useState('')
  const [schedMode, setSchedMode] = useState('HYBRID')
  const [schedVenue, setSchedVenue] = useState('')
  const [schedAgenda, setSchedAgenda] = useState('')
  const [scheduleError, setScheduleError] = useState<string | null>(null)

  // Docket Application Modal
  const [isDocketModalOpen, setIsDocketModalOpen] = useState(false)
  const [docketAppId, setDocketAppId] = useState('')
  const [docketSummary, setDocketSummary] = useState('')
  const [docketRepName, setDocketRepName] = useState('')
  const [docketError, setDocketError] = useState<string | null>(null)

  // Record Attendance Modal
  const [isAttendanceModalOpen, setIsAttendanceModalOpen] = useState(false)
  const [attendanceRecords, setAttendanceRecords] = useState<any[]>([])
  const [attendanceError, setAttendanceError] = useState<string | null>(null)

  // Record Minutes Modal
  const [isMinutesModalOpen, setIsMinutesModalOpen] = useState(false)
  const [minutesText, setMinutesText] = useState('')
  const [finalRec, setFinalRec] = useState('RECOMMEND_APPROVAL')
  const [recSummary, setRecSummary] = useState('')
  const [minutesError, setMinutesError] = useState<string | null>(null)

  // Fetch Hearings
  const { data: hearings = [], isLoading: loadingHearings } = useQuery({
    queryKey: ['hearings'],
    queryFn: () => committeeService.listHearings(),
  })

  // Fetch Committees
  const { data: committees = [], isLoading: loadingCommittees } = useQuery({
    queryKey: ['committees'],
    queryFn: () => committeeService.listCommittees(),
  })

  // Fetch Applications for Docket dropdown
  const { data: apps = [] } = useQuery({
    queryKey: ['applications-for-docket'],
    queryFn: () => applicationService.listApplications(),
  })

  // Schedule Hearing Mutation
  const scheduleMutation = useMutation({
    mutationFn: committeeService.scheduleHearing,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['hearings'] })
      setIsScheduleModalOpen(false)
      setScheduleError(null)
    },
    onError: (err: any) => {
      setScheduleError(err.message || 'Failed to schedule hearing')
    },
  })

  // Add Docket Mutation
  const docketMutation = useMutation({
    mutationFn: (data: { hearingId: string; payload: any }) =>
      committeeService.addDocket(data.hearingId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['hearings'] })
      if (selectedHearing) {
        const updated = await committeeService.getHearing(selectedHearing.id)
        setSelectedHearing(updated)
      }
      setIsDocketModalOpen(false)
      setDocketError(null)
    },
    onError: (err: any) => {
      setDocketError(err.message || 'Failed to docket application')
    },
  })

  // Record Attendance Mutation
  const attendanceMutation = useMutation({
    mutationFn: (data: { hearingId: string; payload: any }) =>
      committeeService.recordAttendance(data.hearingId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['hearings'] })
      if (selectedHearing) {
        const updated = await committeeService.getHearing(selectedHearing.id)
        setSelectedHearing(updated)
      }
      setIsAttendanceModalOpen(false)
      setAttendanceError(null)
    },
    onError: (err: any) => {
      setAttendanceError(err.message || 'Failed to record attendance')
    },
  })

  // Record Minutes Mutation
  const minutesMutation = useMutation({
    mutationFn: (data: { hearingId: string; payload: any }) =>
      committeeService.recordMinutes(data.hearingId, data.payload),
    onSuccess: async () => {
      queryClient.invalidateQueries({ queryKey: ['hearings'] })
      if (selectedHearing) {
        const updated = await committeeService.getHearing(selectedHearing.id)
        setSelectedHearing(updated)
      }
      setIsMinutesModalOpen(false)
      setMinutesError(null)
    },
    onError: (err: any) => {
      setMinutesError(err.message || 'Failed to record minutes')
    },
  })

  const openAttendanceModal = (h: Hearing) => {
    // Find matching committee to get roster
    const comm = committees.find((c) => c.id === h.committee_id)
    if (comm) {
      const records = comm.memberships.map((m) => {
        const existing = h.attendances.find((a) => a.member_name === m.member_name)
        return {
          member_name: m.member_name,
          member_role: m.member_role,
          user_id: m.user_id,
          attended: existing ? existing.attended : true,
          attendance_mode: existing ? existing.attendance_mode : 'IN_PERSON',
        }
      })
      setAttendanceRecords(records)
    }
    setIsAttendanceModalOpen(true)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center">
            <Scale className="w-6 h-6 mr-2.5 text-blue-600" />
            Standing Committees & Hearing Dockets
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Quorum-Governed Standing Hearing Committee (SHC) & Standing Appellate Committee (SAC) Adjudication
          </p>
        </div>

        {isOfficer && activeTab === 'hearings' && (
          <button
            onClick={() => setIsScheduleModalOpen(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Schedule Committee Hearing
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => {
              setActiveTab('hearings')
              setSelectedHearing(null)
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center ${
              activeTab === 'hearings'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Calendar className="w-4 h-4 mr-2" />
            Scheduled Hearings ({hearings.length})
          </button>
          <button
            onClick={() => {
              setActiveTab('benches')
              setSelectedHearing(null)
            }}
            className={`py-3 px-1 border-b-2 font-medium text-sm flex items-center ${
              activeTab === 'benches'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
            }`}
          >
            <Landmark className="w-4 h-4 mr-2" />
            Constituted Benches ({committees.length})
          </button>
        </nav>
      </div>

      {/* Tab 1: Hearings */}
      {activeTab === 'hearings' && (
        <div className="space-y-6">
          {loadingHearings ? (
            <div className="p-8 text-center text-slate-500">Loading committee hearings...</div>
          ) : hearings.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
              <Scale className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <h3 className="text-base font-medium text-slate-900">No committee hearings scheduled</h3>
              <p className="text-sm text-slate-500 mt-1">
                Regional officers may schedule an SHC or SAC hearing session for disputed dockets.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {hearings.map((h) => {
                const attendedCount = h.attendances.filter((a) => a.attended).length
                const targetComm = committees.find((c) => c.id === h.committee_id)
                const quorumReq = targetComm?.quorum_required || 3
                const hasQuorum = attendedCount >= quorumReq

                return (
                  <div
                    key={h.id}
                    className="bg-white border border-slate-200 rounded-lg p-5 hover:border-blue-300 transition-all shadow-sm"
                  >
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-3">
                          <span className="font-mono font-bold text-blue-700 text-base">
                            {h.hearing_number}
                          </span>
                          <StatusBadge status={h.status} />
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800">
                            {h.hearing_type}
                          </span>
                          <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">
                            {h.meeting_mode}
                          </span>
                        </div>
                        <div className="text-sm text-slate-800 font-medium">
                          {h.committee_name || 'Standing Committee'} — Agenda: {h.agenda}
                        </div>
                        <div className="text-xs text-slate-500 flex items-center space-x-4">
                          <span>Date: {formatDate(h.scheduled_date)}</span>
                          <span>Venue: {h.venue_or_link}</span>
                          <span className="font-semibold text-slate-700">
                            Quorum: {attendedCount}/{quorumReq} Present ({hasQuorum ? '✓ Valid' : 'Deficient'})
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <button
                          onClick={() => setSelectedHearing(h)}
                          className="px-3.5 py-1.5 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
                        >
                          Dockets ({h.dockets.length})
                        </button>

                        {isOfficer && (
                          <button
                            onClick={() => {
                              setSelectedHearing(h)
                              openAttendanceModal(h)
                            }}
                            className="px-3.5 py-1.5 border border-blue-300 bg-blue-50 text-blue-700 rounded-md text-sm font-medium hover:bg-blue-100 flex items-center"
                          >
                            <UserCheck className="w-4 h-4 mr-1.5" />
                            Record Attendance
                          </button>
                        )}

                        {isOfficer && ['SCHEDULED', 'NOTICE_ISSUED', 'IN_SESSION', 'MINUTES_PENDING'].includes(h.status) && (
                          <button
                            onClick={() => {
                              setSelectedHearing(h)
                              setIsMinutesModalOpen(true)
                            }}
                            className="px-3.5 py-1.5 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 flex items-center"
                          >
                            <FileText className="w-4 h-4 mr-1.5" />
                            Record Minutes
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Final Recommendation Banner if recorded */}
                    {h.final_recommendation && (
                      <div className="mt-4 p-3 bg-slate-50 border border-slate-200 rounded text-xs flex justify-between items-center">
                        <div>
                          <span className="font-bold text-slate-700">Advisory Recommendation:</span>{' '}
                          <span className="font-bold text-blue-700">{h.final_recommendation}</span> — {h.recommendation_summary}
                        </div>
                        <span className="text-[11px] text-slate-500 italic">
                          (Requires authorized statutory human decision)
                        </span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Benches & Committees */}
      {activeTab === 'benches' && (
        <div className="space-y-6">
          {loadingCommittees ? (
            <div className="p-8 text-center text-slate-500">Loading committee benches...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {committees.map((comm) => (
                <div key={comm.id} className="bg-white border border-slate-200 rounded-lg p-5 shadow-sm space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-base font-bold text-slate-900">{comm.name}</h4>
                      <p className="font-mono text-xs text-blue-700">{comm.code}</p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-purple-100 text-purple-800">
                      {comm.committee_type}
                    </span>
                  </div>

                  <p className="text-xs text-slate-600">{comm.description}</p>

                  <div className="text-xs text-slate-500 flex justify-between pt-2 border-t border-slate-100">
                    <span>
                      <strong>Quorum Required:</strong> {comm.quorum_required} Members
                    </span>
                    <span>
                      <strong>Validity:</strong> {formatDate(comm.valid_from)}
                    </span>
                  </div>

                  {/* Member Roster */}
                  <div className="space-y-1.5 pt-2">
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Bench Roster ({comm.memberships.length}):</h5>
                    {comm.memberships.map((m) => (
                      <div key={m.id} className="p-2 bg-slate-50 rounded border border-slate-100 text-xs flex justify-between items-center">
                        <span className="font-medium text-slate-800">{m.member_name}</span>
                        <span className="text-[11px] px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
                          {m.member_role}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Selected Hearing Details Drawer */}
      {selectedHearing && !isAttendanceModalOpen && !isMinutesModalOpen && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedHearing(null)}
          title={`Hearing Session: ${selectedHearing.hearing_number}`}
        >
          <div className="space-y-6 text-sm">
            <div className="bg-slate-50 p-4 rounded border border-slate-200 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Committee:</span>
                <span>{selectedHearing.committee_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Status:</span>
                <StatusBadge status={selectedHearing.status} />
              </div>
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Scheduled:</span>
                <span>{formatDate(selectedHearing.scheduled_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="font-bold text-slate-700">Agenda:</span>
                <span>{selectedHearing.agenda}</span>
              </div>
            </div>

            {/* Dockets List */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h4 className="text-sm font-bold text-slate-900">Application Dockets on Agenda</h4>
                {isOfficer && ['SCHEDULED', 'NOTICE_ISSUED'].includes(selectedHearing.status) && (
                  <button
                    onClick={() => setIsDocketModalOpen(true)}
                    className="text-xs bg-blue-600 text-white px-2.5 py-1 rounded hover:bg-blue-700 font-medium"
                  >
                    + Add Application Docket
                  </button>
                )}
              </div>

              {selectedHearing.dockets.length === 0 ? (
                <p className="text-xs text-slate-500 italic">No dockets assigned to this hearing session.</p>
              ) : (
                <div className="space-y-2">
                  {selectedHearing.dockets.map((d) => (
                    <div key={d.id} className="p-3 bg-white border border-slate-200 rounded text-xs space-y-1">
                      <div className="flex justify-between font-bold">
                        <span className="text-blue-700">{d.docket_number}</span>
                        <StatusBadge status={d.docket_status} />
                      </div>
                      <div className="text-slate-800 font-medium">{d.institution_name} ({d.application_number})</div>
                      <div className="text-slate-600 text-[11px]">{d.matter_summary}</div>
                      {d.institutional_representative_name && (
                        <div className="text-slate-500 text-[11px]">Rep: {d.institutional_representative_name}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedHearing(null)}
                className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Schedule Hearing Modal */}
      <Modal
        isOpen={isScheduleModalOpen}
        onClose={() => setIsScheduleModalOpen(false)}
        title="Schedule Standing Committee Hearing Session"
      >
        <div className="space-y-4 text-sm">
          {scheduleError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {scheduleError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Constituted Committee</label>
            <select
              value={schedCommitteeId}
              onChange={(e) => {
                setSchedCommitteeId(e.target.value)
                const c = committees.find((x) => x.id === e.target.value)
                if (c) setSchedType(c.committee_type)
              }}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            >
              <option value="">Choose Committee...</option>
              {committees.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.code} - {c.committee_type})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Scheduled Date & Time (UTC)</label>
              <input
                type="datetime-local"
                value={schedDate}
                onChange={(e) => setSchedDate(e.target.value ? new Date(e.target.value).toISOString() : '')}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Meeting Mode</label>
              <select
                value={schedMode}
                onChange={(e) => setSchedMode(e.target.value)}
                className="w-full border border-slate-300 rounded-md p-2 text-sm"
              >
                <option value="HYBRID">Hybrid (Room + Remote Link)</option>
                <option value="PHYSICAL">Physical In-Person Bench</option>
                <option value="VIRTUAL">Virtual Video Hearing</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Venue or Meeting Link</label>
            <input
              type="text"
              placeholder="Regional Office Board Room / Webex Link..."
              value={schedVenue}
              onChange={(e) => setSchedVenue(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Hearing Agenda & Statutory Subject</label>
            <textarea
              rows={3}
              placeholder="Hearing on Faculty Deficiency Appeal and Infrastructure Scrutiny..."
              value={schedAgenda}
              onChange={(e) => setSchedAgenda(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsScheduleModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!schedCommitteeId || !schedDate || !schedVenue || schedAgenda.length < 10 || scheduleMutation.isPending}
              onClick={() => {
                scheduleMutation.mutate({
                  committee_id: schedCommitteeId,
                  hearing_type: schedType,
                  scheduled_date: schedDate,
                  meeting_mode: schedMode,
                  venue_or_link: schedVenue,
                  agenda: schedAgenda,
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {scheduleMutation.isPending ? 'Scheduling...' : 'Confirm Session'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Docket Application Modal */}
      <Modal
        isOpen={isDocketModalOpen}
        onClose={() => setIsDocketModalOpen(false)}
        title="Docket Application for Committee Hearing"
      >
        <div className="space-y-4 text-sm">
          {docketError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {docketError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Target Application</label>
            <select
              value={docketAppId}
              onChange={(e) => setDocketAppId(e.target.value)}
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

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Institutional Representative (Director/Dean)</label>
            <input
              type="text"
              placeholder="Dr. Full Name, Designation..."
              value={docketRepName}
              onChange={(e) => setDocketRepName(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Matter Summary & Specific Grounds of Hearing</label>
            <textarea
              rows={3}
              placeholder="Summary of institutional appeal and disputed findings..."
              value={docketSummary}
              onChange={(e) => setDocketSummary(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsDocketModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={!docketAppId || docketSummary.length < 10 || docketMutation.isPending}
              onClick={() => {
                if (!selectedHearing) return
                docketMutation.mutate({
                  hearingId: selectedHearing.id,
                  payload: {
                    application_id: docketAppId,
                    matter_summary: docketSummary,
                    referred_by: 'REGIONAL_OFFICE',
                    institutional_representative_name: docketRepName || undefined,
                  },
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {docketMutation.isPending ? 'Docketing...' : 'Add to Docket'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Record Attendance Modal with Quorum Evaluation */}
      <Modal
        isOpen={isAttendanceModalOpen}
        onClose={() => setIsAttendanceModalOpen(false)}
        title="Record Member Attendance & Verify Quorum"
      >
        <div className="space-y-4 text-sm">
          {attendanceError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {attendanceError}
            </div>
          )}

          <p className="text-xs text-slate-600">
            Record attendance for all constituted committee bench members. Statutory quorum requires sufficient attending members before recording formal recommendations.
          </p>

          <div className="space-y-2 border border-slate-200 rounded p-3 bg-slate-50">
            {attendanceRecords.map((rec, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 bg-white rounded border border-slate-200 text-xs">
                <div>
                  <span className="font-bold text-slate-800">{rec.member_name}</span>
                  <span className="text-slate-500 ml-2">({rec.member_role})</span>
                </div>

                <div className="flex items-center space-x-4">
                  <label className="flex items-center space-x-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rec.attended}
                      onChange={(e) => {
                        const copy = [...attendanceRecords]
                        copy[idx].attended = e.target.checked
                        setAttendanceRecords(copy)
                      }}
                    />
                    <span className="font-medium text-slate-700">Attended</span>
                  </label>

                  {rec.attended && (
                    <select
                      value={rec.attendance_mode}
                      onChange={(e) => {
                        const copy = [...attendanceRecords]
                        copy[idx].attendance_mode = e.target.value
                        setAttendanceRecords(copy)
                      }}
                      className="border border-slate-300 rounded px-2 py-0.5 text-[11px]"
                    >
                      <option value="IN_PERSON">In Person</option>
                      <option value="REMOTE">Remote Video</option>
                    </select>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsAttendanceModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={attendanceMutation.isPending}
              onClick={() => {
                if (!selectedHearing) return
                attendanceMutation.mutate({
                  hearingId: selectedHearing.id,
                  payload: attendanceRecords,
                })
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {attendanceMutation.isPending ? 'Saving...' : 'Save Attendance'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Record Minutes & Recommendations Modal */}
      <Modal
        isOpen={isMinutesModalOpen}
        onClose={() => setIsMinutesModalOpen(false)}
        title="Record Hearing Minutes & Statutory Recommendation"
      >
        <div className="space-y-4 text-sm">
          {minutesError && (
            <div className="p-3 bg-rose-50 border border-rose-200 rounded text-xs text-rose-700">
              {minutesError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Advisory Recommendation</label>
            <select
              value={finalRec}
              onChange={(e) => setFinalRec(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm font-bold"
            >
              <option value="RECOMMEND_APPROVAL">RECOMMEND STATUTORY APPROVAL</option>
              <option value="RECOMMEND_REJECTION">RECOMMEND STATUTORY REJECTION</option>
              <option value="RECOMMEND_RE_EVC">RECOMMEND RE-INSPECTION (RE-EVC)</option>
              <option value="DISMISSED">DISMISS PETITION / PROCEEDINGS</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Recommendation Summary</label>
            <textarea
              rows={2}
              placeholder="Concise statutory verdict of the committee..."
              value={recSummary}
              onChange={(e) => setRecSummary(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Full Minutes of Meeting</label>
            <textarea
              rows={5}
              placeholder="Record deliberations, arguments presented by institutional representative, and unanimous or majority decision of the bench..."
              value={minutesText}
              onChange={(e) => setMinutesText(e.target.value)}
              className="w-full border border-slate-300 rounded-md p-2 text-sm"
            />
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
            <strong>Statutory Rule Notice:</strong> Committee recommendations are advisory and do not automatically mutate application approval states. Final approval requires explicit human attestation by the authorized Regional Officer or Central Council.
          </div>

          <div className="flex justify-end space-x-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsMinutesModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              disabled={minutesText.length < 20 || recSummary.length < 10 || minutesMutation.isPending}
              onClick={() => {
                if (!selectedHearing) return
                minutesMutation.mutate({
                  hearingId: selectedHearing.id,
                  payload: {
                    minutes_of_meeting: minutesText,
                    final_recommendation: finalRec,
                    recommendation_summary: recSummary,
                  },
                })
              }}
              className="px-4 py-2 bg-emerald-600 text-white rounded-md text-sm font-medium hover:bg-emerald-700 disabled:opacity-50"
            >
              {minutesMutation.isPending ? 'Recording...' : 'Submit Final Minutes'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
