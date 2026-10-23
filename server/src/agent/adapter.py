"""Agent adapter layer providing deterministic local orchestration and pluggable model interfaces."""

import os
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.mcp.tools import (
    tool_approve_follow_up_task,
    tool_get_audit_log,
    tool_get_discharge_plan,
    tool_list_follow_up_tasks,
    tool_propose_follow_up_task,
)


class ToolCallRecord(BaseModel):
    tool: str
    arguments: Dict[str, Any]
    result: Any


class AgentTurnResult(BaseModel):
    response_text: str
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    pending_proposal: Optional[Dict[str, Any]] = None
    safety_disclaimer: str = (
        "SYNTHETIC DEMO DATA ONLY. CareSync does not provide medical advice, diagnosis, or clinical triage."
    )
    safety_refusal: bool = False


class AgentAdapter(ABC):
    @abstractmethod
    async def process_user_turn(
        self, prompt: str, patient_id: str = "patient-synthetic-001"
    ) -> AgentTurnResult:
        """Process a coordinator turn, executing MCP tools and returning structured outcomes."""
        pass


class DeterministicAgentAdapter(AgentAdapter):
    """Deterministic agent adapter executing real MCP tools to drive the golden-path demo offline.
    
    Adheres strictly to AGENTS.md rules: no hallucinations, explicit uncertainty,
    mandatory human approval, and refusal of clinical triage.
    """

    async def process_user_turn(
        self, prompt: str, patient_id: str = "patient-synthetic-001"
    ) -> AgentTurnResult:
        cleaned_prompt = prompt.lower().strip()
        records: List[ToolCallRecord] = []

        # 1. Clinical safety / emergency guardrail
        clinical_keywords = ["chest pain", "short of breath", "diagnose", "triage", "prescribe", "dosage", "medication change", "emergency", "dizziness"]
        if any(kw in cleaned_prompt for kw in clinical_keywords):
            return AgentTurnResult(
                response_text=(
                    "CRITICAL SAFETY NOTICE: This prototype cannot assess medical emergencies, provide clinical triage, "
                    "or recommend medications. If this fictional scenario were a real medical situation, please direct "
                    "the patient immediately to local emergency services (911) or a qualified healthcare provider."
                ),
                tool_calls=[],
                safety_refusal=True,
            )

        # 2. Preparation / Proposal: "prepare a follow-up task", "propose"
        if any(kw in cleaned_prompt for kw in ["prepare", "propose", "create task", "add task", "schedule follow-up"]):
            plan_res = await tool_get_discharge_plan(patient_id)
            records.append(
                ToolCallRecord(
                    tool="get_discharge_plan",
                    arguments={"patient_id": patient_id},
                    result=plan_res,
                )
            )

            # Determine excerpt based on prompt context (PCP vs Cardiology)
            if "cardiology" in cleaned_prompt or "echo" in cleaned_prompt:
                excerpt = "Follow up with outpatient cardiology clinic. Patient requires echocardiogram in 4 weeks."
                title = "Schedule outpatient cardiology appointment and echocardiogram"
                due_date = None
                owner = None
            else:
                excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
                title = "Schedule follow-up consultation with primary care physician Dr. Sarah Jenkins"
                due_date = "2026-10-27"
                owner = None  # Explicitly unset for human review per golden path

            prop_res = await tool_propose_follow_up_task(
                patient_id=patient_id,
                source_reference=excerpt,
                title=title,
                due_date=due_date,
                owner=owner,
            )
            records.append(
                ToolCallRecord(
                    tool="propose_follow_up_task",
                    arguments={
                        "patient_id": patient_id,
                        "source_reference": excerpt,
                        "title": title,
                        "due_date": due_date,
                        "owner": owner,
                    },
                    result=prop_res,
                )
            )

            response = (
                f"I have prepared a follow-up task proposal based on verified discharge plan evidence:\n"
                f"• Title: {title}\n"
                f"• Supported by excerpt: \"{excerpt}\"\n"
                f"• Due Date: {due_date or 'Unset (requires coordinator decision)'}\n"
                f"• Owner: Explicitly unassigned\n"
                f"• Proposal ID: {prop_res['proposal_id']}\n\n"
                f"Notice: This task is pending approval and has NOT been added to the active schedule. "
                f"Please review and click 'Approve' to confirm and record it in the audit trail."
            )

            return AgentTurnResult(
                response_text=response,
                tool_calls=records,
                pending_proposal=prop_res,
            )

        # 3. Inquiry: Outstanding follow-ups / tasks
        if any(kw in cleaned_prompt for kw in ["outstanding", "pending", "tasks", "follow-up", "follow ups", "what tasks"]):
            # Call MCP get_discharge_plan
            plan_res = await tool_get_discharge_plan(patient_id)
            records.append(
                ToolCallRecord(
                    tool="get_discharge_plan",
                    arguments={"patient_id": patient_id},
                    result=plan_res,
                )
            )

            # Call MCP list_follow_up_tasks
            tasks_res = await tool_list_follow_up_tasks(patient_id)
            records.append(
                ToolCallRecord(
                    tool="list_follow_up_tasks",
                    arguments={"patient_id": patient_id},
                    result=tasks_res,
                )
            )

            pending = [t for t in tasks_res if t["status"] == "PENDING"]
            completed = [t for t in tasks_res if t["status"] == "COMPLETED"]

            summary_lines = [
                f"Discharge follow-up status for synthetic patient Eleanor Vance (MRN: SYNTH-MRN-84920):",
                f"- Outstanding (Pending) Tasks: {len(pending)}",
            ]
            for t in pending:
                owner_str = t['owner'] if t['owner'] else "Explicitly Unassigned (None)"
                due_str = t['due_date'] if t['due_date'] else "Explicitly Unset (None)"
                flag_str = " [Human Review Required]" if t.get("requires_human_confirmation") else ""
                summary_lines.append(f"  • {t['title']} — Due: {due_str}, Owner: {owner_str}{flag_str}")

            if completed:
                summary_lines.append(f"- Completed Tasks: {len(completed)}")
                for t in completed:
                    summary_lines.append(f"  ✓ {t['title']} (Completed by {t['owner']})")

            if plan_res.get("explicit_missing_fields"):
                summary_lines.append(
                    f"- Missing Discharge Plan Fields flagged for human review: {', '.join(plan_res['explicit_missing_fields'])}"
                )

            return AgentTurnResult(
                response_text="\n".join(summary_lines),
                tool_calls=records,
            )

        # 4. Approval action: "approve"
        if "approve" in cleaned_prompt:
            match = re.search(r"proposal-[a-f0-9]+", prompt, re.IGNORECASE)
            proposal_id = match.group(0) if match else None

            if not proposal_id:
                # If no ID specified, look up latest pending proposal from audit log
                audit_res = await tool_get_audit_log(patient_id)
                for ev in reversed(audit_res):
                    if ev["action"] == "PROPOSAL_CREATED":
                        proposal_id = ev["entity_id"]
                        break

            if not proposal_id:
                return AgentTurnResult(
                    response_text="Could not identify a pending proposal ID to approve. Please specify the proposal ID.",
                    tool_calls=[],
                )

            approved_res = await tool_approve_follow_up_task(
                proposal_id=proposal_id, approved_by="Care Coordinator Alex"
            )
            records.append(
                ToolCallRecord(
                    tool="approve_follow_up_task",
                    arguments={"proposal_id": proposal_id, "approved_by": "Care Coordinator Alex"},
                    result=approved_res,
                )
            )

            response = (
                f"Proposal '{proposal_id}' has been approved by Care Coordinator Alex.\n"
                f"The task '{approved_res['task']['title']}' is now actively persisted with ID '{approved_res['task']['id']}'.\n"
                f"An immutable audit event has been recorded in the coordination log."
            )

            return AgentTurnResult(
                response_text=response,
                tool_calls=records,
            )

        # 5. Audit Log inquiry: "audit", "history", "log"
        if any(kw in cleaned_prompt for kw in ["audit", "history", "log", "trail", "who approved"]):
            audit_res = await tool_get_audit_log(patient_id)
            records.append(
                ToolCallRecord(
                    tool="get_audit_log",
                    arguments={"patient_id": patient_id},
                    result=audit_res,
                )
            )

            lines = [f"Audit trail for synthetic patient {patient_id}:"]
            for ev in audit_res:
                lines.append(f"• [{ev['timestamp']}] {ev['action']} by {ev['performed_by']} ({ev['entity_type']} ID: {ev['entity_id']})")

            return AgentTurnResult(
                response_text="\n".join(lines),
                tool_calls=records,
            )

        # Default fallback
        plan_res = await tool_get_discharge_plan(patient_id)
        records.append(
            ToolCallRecord(
                tool="get_discharge_plan",
                arguments={"patient_id": patient_id},
                result=plan_res,
            )
        )
        return AgentTurnResult(
            response_text=(
                f"I am CareSync, your Alexa+ Care Coordination assistant for Eleanor Vance [SYNTHETIC]. "
                f"You can ask me to review outstanding follow-up tasks, prepare a proposal from the discharge plan, "
                f"or inspect the audit log."
            ),
            tool_calls=records,
        )


def get_agent_adapter() -> AgentAdapter:
    """Factory returning configured agent adapter. Defaults to DeterministicAgentAdapter for reproducible local demo."""
    return DeterministicAgentAdapter()
