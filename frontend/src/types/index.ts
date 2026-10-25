export interface RoleBrief {
  code: string;
  name: string;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  designation?: string;
  institution_id?: string;
  institution_name?: string;
  assigned_region?: string;
  roles: RoleBrief[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  user: UserProfile;
}

export interface Institution {
  id: string;
  name: string;
  code: string;
  region: string;
  state: string;
  district: string;
  institution_type: string;
  established_year?: number;
  status: string;
  contact_email: string;
  contact_phone: string;
  address?: string;
  created_at: string;
  updated_at: string;
}

export interface WorkflowVersionBrief {
  id: string;
  version_number: number;
  aph_edition: string;
  is_published: boolean;
  created_at: string;
}

export interface WorkflowTemplate {
  id: string;
  code: string;
  name: string;
  description?: string;
  category: string;
  is_active: boolean;
  versions: WorkflowVersionBrief[];
}

export interface ApplicationEvent {
  id: string;
  actor_id: string;
  event_type: string;
  from_status?: string;
  to_status?: string;
  remarks?: string;
  event_payload_json?: string;
  created_at: string;
}

export interface DelayRiskFactor {
  factor: string;
  impact: 'LOW' | 'MEDIUM' | 'HIGH';
  detail: string;
}

export interface Application {
  id: string;
  application_number: string;
  institution_id: string;
  template_id: string;
  version_id: string;
  current_status: string;
  academic_year: string;
  submission_data_json: string;
  submission_date?: string;
  sla_deadline?: string;
  applicant_user_id: string;
  assigned_scrutiny_officer_id?: string;
  assigned_regional_officer_id?: string;
  delay_risk_score?: number;
  delay_risk_factors_json?: string;
  created_at: string;
  updated_at: string;
  events: ApplicationEvent[];
}

export interface AuditEvent {
  id: string;
  sequence_number: number;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address?: string;
  previous_entry_hash: string;
  payload_hash: string;
  entry_hash: string;
  details_json?: string;
  created_at: string;
}

export interface AuditVerification {
  is_valid: boolean;
  total_events_checked: number;
  last_verified_sequence: number;
  broken_sequence_id?: string;
  chain_head_hash?: string;
  verification_message: string;
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  storage_key: string;
  sha256_hash: string;
  file_size: number;
  uploaded_by_user_id: string;
  scan_status: string;
  created_at: string;
}

export interface Document {
  id: string;
  application_id: string;
  institution_id: string;
  category: string;
  original_filename: string;
  storage_key: string;
  mime_type: string;
  file_size: number;
  sha256_hash: string;
  uploaded_by_user_id: string;
  scan_status: 'QUARANTINED' | 'SCANNING' | 'ACCEPTED' | 'REJECTED';
  scan_result_details?: string;
  scan_timestamp?: string;
  rejection_reason?: string;
  verification_status: 'PENDING' | 'ACCEPTED' | 'DEFICIENT' | 'REQUIRES_MANUAL_VERIFICATION';
  current_version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  versions: DocumentVersion[];
}

export interface ScrutinyFinding {
  id: string;
  application_id: string;
  document_id?: string;
  category: string;
  officer_id: string;
  finding_status: 'ACCEPTED' | 'DEFICIENT' | 'REQUIRES_MANUAL_VERIFICATION';
  reason: string;
  notes?: string;
  is_advisory_ai: boolean;
  created_at: string;
  updated_at: string;
}

export interface DeficiencyItem {
  id: string;
  notice_id: string;
  document_id?: string;
  requirement_title: string;
  description: string;
  required_corrective_action: string;
  item_status: string;
  created_at: string;
}

export interface DeficiencyResponseModel {
  id: string;
  notice_id: string;
  submitted_by_user_id: string;
  response_remarks: string;
  attachments_json: string;
  created_at: string;
}

export interface DeficiencyNotice {
  id: string;
  notice_number: string;
  application_id: string;
  institution_id: string;
  issuing_officer_id: string;
  status: 'DRAFT' | 'ISSUED' | 'RESPONSE_SUBMITTED' | 'UNDER_REVIEW' | 'RESOLVED' | 'REOPENED';
  due_date: string;
  officer_remarks?: string;
  issued_at?: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  items: DeficiencyItem[];
  responses: DeficiencyResponseModel[];
}

export interface NotificationItem {
  id: string;
  user_id?: string;
  institution_id?: string;
  title: string;
  message: string;
  category: string;
  link_url?: string;
  is_read: boolean;
  delivery_status: string;
  created_at: string;
}

// --- M06: EVC Inspections & Expert Pool ---

export interface Expert {
  id: string;
  user_id?: string;
  name: string;
  email: string;
  phone?: string;
  designation: string;
  organization: string;
  expert_type: string;
  qualifications: string;
  experience_years: number;
  specializations: string[];
  affiliated_institution_ids: string[];
  alma_mater: string;
  state: string;
  district: string;
  availability_status: string;
  conflict_declarations: string[];
  is_active: boolean;
  verification_status: string;
  created_at: string;
  updated_at: string;
}

export interface ConflictCheckResult {
  expert_id: string;
  expert_name: string;
  application_id: string;
  institution_id: string;
  institution_name: string;
  has_conflict: boolean;
  is_blocked: boolean;
  policy_version: string;
  conflict_reasons: string[];
}

export interface EVCPanelMember {
  id: string;
  inspection_id: string;
  expert_id: string;
  expert_name: string;
  expert_designation: string;
  expert_organization: string;
  role: string;
  conflict_check_passed: boolean;
  conflict_notes?: string;
  attendance_status: string;
  attendance_timestamp?: string;
  sign_off_status: string;
  sign_off_timestamp?: string;
  sign_off_remarks?: string;
}

export interface EVCReportVersion {
  id: string;
  inspection_id: string;
  version_number: number;
  application_id: string;
  submitted_by_user_id: string;
  submitted_by_name?: string;
  submitted_at: string;
  sha256_hash: string;
  overall_recommendation: string;
  infrastructure_score?: number;
  faculty_verification_status: string;
  land_building_status: string;
  laboratories_equipment_status: string;
  safety_and_amenities_status: string;
  observations: string;
  deficiencies_identified?: string;
  checklist_data: Record<string, any>;
  evidence_references: string[];
  location_evidence: Record<string, any>;
  virtual_attendance: Record<string, any>;
  review_status: string;
  reviewed_by_user_id?: string;
  reviewed_by_name?: string;
  reviewed_at?: string;
  review_remarks?: string;
  created_at: string;
}

export interface EVCInspection {
  id: string;
  application_id: string;
  institution_id: string;
  institution_name?: string;
  inspection_number: string;
  inspection_mode: string;
  status: string;
  scheduled_start_date: string;
  scheduled_end_date: string;
  actual_inspection_date?: string;
  chairperson_id?: string;
  chairperson_name?: string;
  meeting_link?: string;
  location_coordinates?: string;
  location_address?: string;
  cancellation_reason?: string;
  assigned_by_user_id: string;
  panel_members: EVCPanelMember[];
  latest_report?: EVCReportVersion;
  created_at: string;
  updated_at: string;
}

// --- M07: Committee Hearings & Docketing ---

export interface CommitteeMembership {
  id: string;
  committee_id: string;
  user_id?: string;
  expert_id?: string;
  member_name: string;
  member_role: string;
  conflict_declarations: string[];
  is_active: boolean;
  created_at: string;
}

export interface Committee {
  id: string;
  code: string;
  name: string;
  committee_type: string;
  description?: string;
  quorum_required: number;
  valid_from: string;
  valid_to?: string;
  is_active: boolean;
  memberships: CommitteeMembership[];
  created_at: string;
  updated_at: string;
}

export interface HearingDocket {
  id: string;
  hearing_id: string;
  application_id: string;
  institution_id: string;
  institution_name?: string;
  application_number?: string;
  docket_number: string;
  matter_summary: string;
  referred_by: string;
  institutional_representative_name?: string;
  docket_status: string;
  docket_recommendation?: string;
  docket_remarks?: string;
  created_at: string;
}

export interface HearingAttendance {
  id: string;
  hearing_id: string;
  member_name: string;
  member_role: string;
  user_id?: string;
  attended: boolean;
  attendance_mode: string;
  conflict_declared_for_docket_ids?: string;
  created_at: string;
}

export interface Hearing {
  id: string;
  committee_id: string;
  committee_name?: string;
  hearing_number: string;
  hearing_type: string;
  status: string;
  scheduled_date: string;
  meeting_mode: string;
  venue_or_link: string;
  agenda: string;
  postponement_reason?: string;
  cancellation_reason?: string;
  chairperson_name?: string;
  conducted_at?: string;
  minutes_of_meeting?: string;
  final_recommendation?: string;
  recommendation_summary?: string;
  dockets: HearingDocket[];
  attendances: HearingAttendance[];
  created_at: string;
  updated_at: string;
}

// --- Authorized Statutory Decisions ---

export interface DecisionCondition {
  id: string;
  decision_id: string;
  condition_code: string;
  description: string;
  due_date: string;
  compliance_status: string;
  created_at: string;
}

export interface StatutoryDecision {
  id: string;
  application_id: string;
  application_number?: string;
  institution_id: string;
  institution_name?: string;
  decision_number: string;
  decision_type: string;
  academic_year: string;
  authority_role: string;
  authorized_by_user_id: string;
  authorized_by_name?: string;
  authorized_at: string;
  governing_policy_version: string;
  reasons: string;
  evidence_references: string[];
  intake_approved?: number;
  valid_for_years: number;
  is_final: boolean;
  is_reconsidered: boolean;
  reconsideration_reference?: string;
  sha256_attestation: string;
  declaration_text: string;
  conditions: DecisionCondition[];
  created_at: string;
}
