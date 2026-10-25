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
