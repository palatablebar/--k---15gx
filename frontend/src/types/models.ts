export type Role = 'admin' | 'dpo' | 'client';
export type PiiType = 'mobile' | 'id_card' | 'email' | 'name' | 'address';
export type MaskMethod = 'mask' | 'hash' | 'generalize' | 'suppress';
export type SensitivityLevel = 'low' | 'medium' | 'high' | 'critical';
export type ColumnRole = 'direct_id' | 'quasi_id' | 'sensitive' | 'non_sensitive';
export type ExportStatus = 'pending' | 'approved' | 'rejected';
export type BuildStatus = 'idle' | 'queued' | 'running' | 'done' | 'failed';
export type CheckStatus = 'queued' | 'running' | 'succeeded' | 'failed';

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  organization: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string | null;
}

export interface DatasetTable {
  id: string;
  schema_name: string;
  table_name: string;
  display_name: string;
  description: string;
  business_domain: string;
  row_count: number;
  column_count: number;
  sensitivity_level: SensitivityLevel;
  owner_note: string;
  last_profiled_at: string | null;
  pii_column_count: number;
}

export interface DatasetColumn {
  id: string;
  table_id: string;
  name: string;
  data_type: string;
  ordinal: number;
  column_role: ColumnRole;
  sensitivity_level: SensitivityLevel;
  null_ratio: number;
  distinct_ratio: number;
  pii_type: PiiType | null;
  pii_confidence: number;
  sample_values: string[];
  current_policy_id: string | null;
  is_scanned: boolean;
  scanned_at: string | null;
}

export interface PiiSummary {
  finding_count: number;
  total_matched: number;
  checksum_checked: number;
  checksum_passed: number;
  by_type: Record<string, number>;
}

export interface TableDetail {
  table: DatasetTable;
  columns: DatasetColumn[];
  pii_summary: PiiSummary;
}

export interface EvidenceSample {
  value: string;
  display_value: string;
  kind: 'match' | 'miss';
  span_start: number;
  span_end: number;
  validation: 'passed' | 'failed' | 'not_applicable';
  note: string;
}

export interface PiiFinding {
  id: string;
  column_id: string;
  column_name: string;
  table_id: string;
  table_name: string;
  pii_type: PiiType;
  scanned_rows: number;
  candidate_rows: number;
  matched_count: number;
  checksum_checked_count: number;
  checksum_pass_count: number;
  hit_rate: number;
  checksum_pass_rate: number;
  uniqueness_penalty: number;
  confidence: number;
  algorithm_version: string;
  sample_values: string[];
  evidence: EvidenceSample[];
  created_at: string | null;
}

export interface ScanResult {
  table_id: string;
  table_name: string;
  columns_scanned: number;
  findings: number;
  total_matched: number;
  checksum_passed: number;
  duration_ms: number;
  findings_detail: PiiFinding[];
  message: string;
}

export interface MaskingPolicy {
  id: string;
  name: string;
  table_id: string | null;
  table_name: string | null;
  column_pattern: string;
  pii_type: PiiType | null;
  method: MaskMethod;
  params: Record<string, unknown>;
  description: string;
  is_active: boolean;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PreviewSample {
  before: string;
  after: string;
  removable_span: number[];
}

export interface PreviewColumn {
  column_id: string;
  column_name: string;
  data_type: string;
  pii_type: PiiType | null;
  method: MaskMethod;
  total_rows: number;
  changed_rows: number;
  distinct_before: number;
  distinct_after: number;
  samples: PreviewSample[];
}

export interface PolicyPreview {
  policy_id: string;
  policy_name: string;
  method: MaskMethod;
  params: Record<string, unknown>;
  total_rows: number;
  applied_columns: PreviewColumn[];
  warnings: string[];
}

export interface KanonCandidate {
  levels: Record<string, number>;
  level_labels: Record<string, string>;
  k: number;
  l: number;
  class_count: number;
  information_loss: number;
  level_loss: number;
  distinct_loss: number;
  passed: boolean;
}

export interface EquivalenceClass {
  qi: Record<string, string>;
  size: number;
  sensitive_values: string[];
}

export interface KanonCheck {
  id: string;
  table_id: string;
  table_name: string;
  quasi_identifiers: string[];
  sensitive_column: string;
  target_k: number;
  target_l: number;
  status: CheckStatus;
  base_k: number | null;
  base_l: number | null;
  final_k: number | null;
  final_l: number | null;
  passed: boolean | null;
  recommended_level: {
    levels?: Record<string, number>;
    level_labels?: Record<string, string>;
    information_loss?: number;
    class_count?: number;
  };
  candidates: KanonCandidate[];
  equivalence_classes: EquivalenceClass[];
  class_size_histogram: Record<string, number>;
  information_loss: number | null;
  conclusion: string;
  error_detail: string | null;
  task_id: string | null;
  created_by_email: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface ExportRequest {
  id: string;
  table_id: string;
  table_name: string;
  table_display_name: string;
  requester_id: string;
  requester_email: string;
  requester_name: string;
  purpose: string;
  requested_rows: number;
  dataset_version: string;
  status: ExportStatus;
  build_status: BuildStatus;
  review_note: string;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  file_digest: string | null;
  masked_rows: number | null;
  applied_policies: string[];
  error_detail: string | null;
  created_at: string | null;
}

export interface AuditLog {
  id: string;
  actor_email: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  detail: Record<string, unknown>;
  ip: string;
  trace_id: string;
  created_at: string | null;
}
