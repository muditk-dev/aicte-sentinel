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
