"""Implementation of the 5 required CareSync MCP tools."""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.db.connection import get_db
from src.db.repository import CareSyncRepository
from src.domain.enums import AuditAction, ProposalStatus, TaskStatus
from src.domain.models import AuditEvent, TaskProposal
from src.domain.source_validator import validate_source_reference


async def tool_get_discharge_plan(
    patient_id: str, db_path_override: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve synthetic discharge plan summary, source excerpts, and explicit missing fields."""
    if not patient_id.startswith("patient-synthetic") and "synth" not in patient_id.lower():
        raise ValueError("Only synthetic patient IDs are allowed.")

    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)
        patient = await repo.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Synthetic patient '{patient_id}' not found.")

        plan = await repo.get_discharge_plan_by_patient_id(patient_id)
        if not plan:
            raise ValueError(f"No discharge plan found for patient '{patient_id}'.")

        return {
            "patient_id": plan.patient_id,
            "admission_date": plan.admission_date,
            "discharge_date": plan.discharge_date,
            "summary": plan.summary,
            "source_text": plan.source_text,
            "source_excerpts": plan.source_excerpts,
            "explicit_missing_fields": plan.explicit_missing_fields,
            "is_synthetic": True,
        }


async def tool_list_follow_up_tasks(
    patient_id: str,
    status: Optional[str] = None,
    db_path_override: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List existing follow-up tasks with their status, source references, and owners/dates."""
    task_status: Optional[TaskStatus] = None
    if status:
        try:
            task_status = TaskStatus(status.upper())
        except ValueError:
            raise ValueError(f"Invalid task status '{status}'. Must be PENDING, COMPLETED, or CANCELLED.")

    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)
        tasks = await repo.list_tasks(patient_id, status=task_status)
        return [
            {
                "id": t.id,
                "patient_id": t.patient_id,
                "title": t.title,
                "status": t.status.value,
                "due_date": t.due_date,
                "owner": t.owner,
                "source_reference": t.source_reference,
                "requires_human_confirmation": t.requires_human_confirmation,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]


async def tool_propose_follow_up_task(
    patient_id: str,
    source_reference: str,
    title: str,
    due_date: Optional[str] = None,
    owner: Optional[str] = None,
    db_path_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a pending follow-up task proposal for human review.
    
    Validates source_reference against the patient's discharge plan.
    Does NOT persist as an approved task. Missing dates or owners remain None.
    """
    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)
        patient = await repo.get_patient(patient_id)
        if not patient:
            raise ValueError(f"Patient '{patient_id}' not found.")

        plan = await repo.get_discharge_plan_by_patient_id(patient_id)
        if not plan:
            raise ValueError(f"No discharge plan exists for patient '{patient_id}'.")

        # Validate source reference against the actual discharge plan
        if not validate_source_reference(source_reference, plan):
            raise ValueError(
                f"Source reference '{source_reference}' could not be verified against the patient's discharge plan. "
                "Proposing unsupported or fabricated tasks is strictly prohibited."
            )

        now = datetime.now(timezone.utc)
        proposal_id = f"proposal-{uuid.uuid4().hex[:8]}"
        proposal = TaskProposal(
            id=proposal_id,
            patient_id=patient_id,
            title=title.strip(),
            due_date=due_date.strip() if due_date else None,
            owner=owner.strip() if owner else None,
            source_reference=source_reference.strip(),
            status=ProposalStatus.PENDING,
            proposed_by="agent-alexa-simulator",
            created_at=now,
        )

        audit_event = AuditEvent(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            patient_id=patient_id,
            action=AuditAction.PROPOSAL_CREATED,
            entity_type="proposal",
            entity_id=proposal.id,
            performed_by="agent-alexa-simulator",
            details={
                "title": proposal.title,
                "source_reference": proposal.source_reference,
                "due_date": proposal.due_date,
                "owner": proposal.owner,
            },
            timestamp=now,
        )

        await repo.create_proposal(proposal)
        await repo.record_audit_event(audit_event)

        return {
            "proposal_id": proposal.id,
            "patient_id": proposal.patient_id,
            "title": proposal.title,
            "status": proposal.status.value,
            "due_date": proposal.due_date,
            "owner": proposal.owner,
            "source_reference": proposal.source_reference,
            "proposed_by": proposal.proposed_by,
            "message": "Proposal created and pending human approval. Not yet persisted as an active task.",
        }


async def tool_approve_follow_up_task(
    proposal_id: str,
    approved_by: str,
    db_path_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Explicitly approve a pending proposal, persist the task, and log audit events atomically.
    
    Safe to retry: repeated approval will not duplicate tasks or audit events.
    """
    if not approved_by or not approved_by.strip():
        raise ValueError("Approver identifier ('approved_by') is required.")

    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)
        task = await repo.approve_proposal(proposal_id=proposal_id, approved_by=approved_by.strip())

        return {
            "status": "APPROVED",
            "proposal_id": proposal_id,
            "approved_by": approved_by,
            "task": {
                "id": task.id,
                "patient_id": task.patient_id,
                "title": task.title,
                "status": task.status.value,
                "due_date": task.due_date,
                "owner": task.owner,
                "source_reference": task.source_reference,
                "requires_human_confirmation": task.requires_human_confirmation,
            },
            "message": "Proposal approved. Follow-up task persisted to active workflow.",
        }


async def tool_get_audit_log(
    patient_id: str, db_path_override: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve full audit log trail for a synthetic patient."""
    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)
        events = await repo.list_audit_events(patient_id)
        return [
            {
                "id": e.id,
                "patient_id": e.patient_id,
                "action": e.action.value,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "performed_by": e.performed_by,
                "details": e.details,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
