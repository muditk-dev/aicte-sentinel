import { apiRequest } from '../lib/api'
import {
  Committee,
  CommitteeMembership,
  Hearing,
  HearingDocket,
  HearingAttendance,
} from '../types'

export const committeeService = {
  // Committees
  async listCommittees(type?: string): Promise<Committee[]> {
    const qs = type ? `?committee_type=${type}` : ''
    return apiRequest<Committee[]>(`/committees${qs}`)
  },

  async createCommittee(payload: {
    code: string
    name: string
    committee_type: string
    description?: string
    quorum_required: number
    valid_from: string
    valid_to?: string
  }): Promise<Committee> {
    return apiRequest<Committee>('/committees', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getCommittee(id: string): Promise<Committee> {
    return apiRequest<Committee>(`/committees/${id}`)
  },

  async addMember(
    committeeId: string,
    payload: {
      user_id?: string
      expert_id?: string
      member_name: string
      member_role: string
      conflict_declarations?: string[]
    }
  ): Promise<CommitteeMembership> {
    return apiRequest<CommitteeMembership>(`/committees/${committeeId}/members`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  // Hearings
  async listHearings(filters?: { committee_id?: string; status?: string; hearing_type?: string }): Promise<Hearing[]> {
    const params = new URLSearchParams()
    if (filters?.committee_id) params.append('committee_id', filters.committee_id)
    if (filters?.status) params.append('status', filters.status)
    if (filters?.hearing_type) params.append('hearing_type', filters.hearing_type)
    const qs = params.toString() ? `?${params.toString()}` : ''
    return apiRequest<Hearing[]>(`/hearings${qs}`)
  },

  async scheduleHearing(payload: {
    committee_id: string
    hearing_type: string
    scheduled_date: string
    meeting_mode: string
    venue_or_link: string
    agenda: string
    chairperson_name?: string
  }): Promise<Hearing> {
    return apiRequest<Hearing>('/hearings', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async getHearing(id: string): Promise<Hearing> {
    return apiRequest<Hearing>(`/hearings/${id}`)
  },

  async addDocket(
    hearingId: string,
    payload: {
      application_id: string
      matter_summary: string
      referred_by: string
      institutional_representative_name?: string
    }
  ): Promise<HearingDocket> {
    return apiRequest<HearingDocket>(`/hearings/${hearingId}/dockets`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async recordAttendance(
    hearingId: string,
    payload: Array<{
      member_name: string
      member_role: string
      user_id?: string
      attended: boolean
      attendance_mode: string
      conflict_declared_for_docket_ids?: string
    }>
  ): Promise<HearingAttendance[]> {
    return apiRequest<HearingAttendance[]>(`/hearings/${hearingId}/attendance`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async transitionHearing(
    hearingId: string,
    targetStatus: string,
    reason?: string
  ): Promise<Hearing> {
    return apiRequest<Hearing>(`/hearings/${hearingId}/transition`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus, reason }),
    })
  },

  async recordMinutes(
    hearingId: string,
    payload: {
      minutes_of_meeting: string
      final_recommendation: string
      recommendation_summary: string
      docket_outcomes?: Array<{
        docket_id: string
        status: string
        recommendation: string
        remarks: string
      }>
    }
  ): Promise<Hearing> {
    return apiRequest<Hearing>(`/hearings/${hearingId}/minutes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
