/**
 * API client connecting the Next.js Simulator directly to the live CareSync FastAPI + MCP backend.
 * Zero client-side mock data; all state comes from the running server.
 */

import {
  AgentTurnResponse,
  AuditEvent,
  FollowUpTask,
  HealthStatus,
  PatientContextResponse,
  TaskProposal,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({}));
      const detail = errorBody.detail || `HTTP ${res.status}: ${res.statusText}`;
      throw new Error(detail);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    console.error(`[CareSync API Error] ${endpoint}:`, err);
    throw err;
  }
}

export async function fetchHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/health");
}

export async function fetchPatientContext(
  patientId: string = "patient-synthetic-001"
): Promise<PatientContextResponse> {
  return request<PatientContextResponse>(`/api/v1/context?patient_id=${encodeURIComponent(patientId)}`);
}

export async function fetchTasks(
  patientId: string = "patient-synthetic-001",
  status?: string
): Promise<FollowUpTask[]> {
  const query = new URLSearchParams({ patient_id: patientId });
  if (status) query.set("status", status);
  return request<FollowUpTask[]>(`/api/v1/tasks?${query.toString()}`);
}

export async function fetchProposals(
  patientId: string = "patient-synthetic-001",
  status?: string
): Promise<TaskProposal[]> {
  const query = new URLSearchParams({ patient_id: patientId });
  if (status) query.set("status", status);
  return request<TaskProposal[]>(`/api/v1/proposals?${query.toString()}`);
}

export async function fetchAuditEvents(
  patientId: string = "patient-synthetic-001"
): Promise<AuditEvent[]> {
  return request<AuditEvent[]>(`/api/v1/audit?patient_id=${encodeURIComponent(patientId)}`);
}

export async function sendAgentMessage(
  prompt: string,
  patientId: string = "patient-synthetic-001"
): Promise<AgentTurnResponse> {
  return request<AgentTurnResponse>("/api/v1/agent/chat", {
    method: "POST",
    body: JSON.stringify({ prompt, patient_id: patientId }),
  });
}

export async function approveProposal(
  proposalId: string,
  approvedBy: string = "Care Coordinator Alex"
): Promise<FollowUpTask> {
  return request<FollowUpTask>("/api/v1/tasks/approve", {
    method: "POST",
    body: JSON.stringify({ proposal_id: proposalId, approved_by: approvedBy }),
  });
}

export async function rejectProposal(
  proposalId: string,
  rejectedBy: string = "Care Coordinator Alex",
  reason: string = "Dismissed by care coordinator in simulator"
): Promise<TaskProposal> {
  return request<TaskProposal>("/api/v1/tasks/reject", {
    method: "POST",
    body: JSON.stringify({
      proposal_id: proposalId,
      rejected_by: rejectedBy,
      reason,
    }),
  });
}

export async function proposeTaskDirect(
  patientId: string,
  title: string,
  sourceReference: string,
  dueDate: string | null = null,
  owner: string | null = null
): Promise<{ proposal_id: string; status: string; patient_id: string }> {
  return request<{ proposal_id: string; status: string; patient_id: string }>(
    "/api/v1/tasks/propose",
    {
      method: "POST",
      body: JSON.stringify({
        patient_id: patientId,
        title,
        source_reference: sourceReference,
        due_date: dueDate,
        owner,
      }),
    }
  );
}
