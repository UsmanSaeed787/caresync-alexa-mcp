/**
 * TypeScript type definitions for CareSync Simulator UI.
 * Matches FastAPI backend and MCP Streamable HTTP tool outputs.
 */

export interface HealthStatus {
  status: string;
  service: string;
  synthetic_data_mode: boolean;
  database: string;
  version: string;
  mcp_endpoint: string;
}

export interface Patient {
  id: string;
  mrn: string;
  full_name: string;
  date_of_birth: string;
  is_synthetic: boolean;
  created_at: string;
}

export interface SourceExcerpt {
  label: string;
  excerpt: string;
}

export interface DischargePlan {
  id: string;
  patient_id: string;
  admission_date: string;
  discharge_date: string;
  summary: string;
  source_text: string;
  source_excerpts: SourceExcerpt[];
  explicit_missing_fields: string[];
  created_at: string;
}

export interface PatientContextResponse {
  patient: Patient;
  discharge_plan: DischargePlan | null;
  safety_disclaimer: string;
}

export interface FollowUpTask {
  id: string;
  patient_id: string;
  title: string;
  status: "PENDING" | "COMPLETED" | "CANCELLED";
  due_date: string | null;
  owner: string | null;
  source_reference: string;
  requires_human_confirmation: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskProposal {
  id: string;
  patient_id: string;
  title: string;
  due_date: string | null;
  owner: string | null;
  source_reference: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  proposed_by: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  patient_id: string;
  action: "PROPOSAL_CREATED" | "PROPOSAL_APPROVED" | "PROPOSAL_REJECTED" | "TASK_CREATED" | "TASK_UPDATED" | "TASK_STATUS_CHANGED" | string;
  entity_type: "task" | "proposal" | string;
  entity_id: string;
  performed_by: string;
  details: Record<string, any>;
  timestamp: string;
}

export interface ToolCallTrace {
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
}

export interface PendingProposalSummary {
  proposal_id: string;
  title: string;
  source_reference: string;
  due_date: string | null;
  owner: string | null;
}

export interface AgentTurnResponse {
  response_text: string;
  tool_calls: ToolCallTrace[];
  pending_proposal: PendingProposalSummary | null;
  safety_refusal: boolean;
  error: string | null;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "alexa" | "system";
  text: string;
  timestamp: string;
  toolCalls?: ToolCallTrace[];
  pendingProposal?: PendingProposalSummary | null;
  safetyRefusal?: boolean;
}
