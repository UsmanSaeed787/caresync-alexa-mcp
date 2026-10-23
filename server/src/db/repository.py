"""Repository layer for CareSync domain entities."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, List, Optional
import aiosqlite

from src.db.connection import transaction
from src.domain.enums import AuditAction, ProposalStatus, TaskStatus
from src.domain.models import AuditEvent, DischargePlan, FollowUpTask, Patient, TaskProposal


class CareSyncRepository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    # ---------------------------------------------------------
    # Patient Operations
    # ---------------------------------------------------------
    async def get_patient(self, patient_id: str) -> Optional[Patient]:
        async with self.db.execute(
            "SELECT id, mrn, full_name, date_of_birth, is_synthetic, created_at FROM patients WHERE id = ?;",
            (patient_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return Patient(
                id=row["id"],
                mrn=row["mrn"],
                full_name=row["full_name"],
                date_of_birth=row["date_of_birth"],
                is_synthetic=bool(row["is_synthetic"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    async def create_patient(self, patient: Patient) -> Patient:
        async with transaction(self.db):
            await self.db.execute(
                """
                INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    patient.id,
                    patient.mrn,
                    patient.full_name,
                    patient.date_of_birth,
                    1 if patient.is_synthetic else 0,
                    patient.created_at.isoformat(),
                ),
            )
        return patient

    # ---------------------------------------------------------
    # Discharge Plan Operations
    # ---------------------------------------------------------
    async def get_discharge_plan_by_patient_id(self, patient_id: str) -> Optional[DischargePlan]:
        async with self.db.execute(
            """
            SELECT id, patient_id, admission_date, discharge_date, summary, source_text,
                   source_excerpts, explicit_missing_fields, created_at
            FROM discharge_plans
            WHERE patient_id = ?;
            """,
            (patient_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return DischargePlan(
                id=row["id"],
                patient_id=row["patient_id"],
                admission_date=row["admission_date"],
                discharge_date=row["discharge_date"],
                summary=row["summary"],
                source_text=row["source_text"],
                source_excerpts=json.loads(row["source_excerpts"]),
                explicit_missing_fields=json.loads(row["explicit_missing_fields"]),
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    async def create_discharge_plan(self, plan: DischargePlan) -> DischargePlan:
        async with transaction(self.db):
            await self.db.execute(
                """
                INSERT INTO discharge_plans (
                    id, patient_id, admission_date, discharge_date, summary, source_text,
                    source_excerpts, explicit_missing_fields, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    plan.id,
                    plan.patient_id,
                    plan.admission_date,
                    plan.discharge_date,
                    plan.summary,
                    plan.source_text,
                    json.dumps(plan.source_excerpts),
                    json.dumps(plan.explicit_missing_fields),
                    plan.created_at.isoformat(),
                ),
            )
        return plan

    # ---------------------------------------------------------
    # Follow-Up Task Operations
    # ---------------------------------------------------------
    async def get_task(self, task_id: str) -> Optional[FollowUpTask]:
        async with self.db.execute(
            """
            SELECT id, patient_id, title, status, due_date, owner, source_reference,
                   requires_human_confirmation, created_at, updated_at
            FROM follow_up_tasks
            WHERE id = ?;
            """,
            (task_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return FollowUpTask(
                id=row["id"],
                patient_id=row["patient_id"],
                title=row["title"],
                status=TaskStatus(row["status"]),
                due_date=row["due_date"],
                owner=row["owner"],
                source_reference=row["source_reference"],
                requires_human_confirmation=bool(row["requires_human_confirmation"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )

    async def list_tasks(
        self, patient_id: str, status: Optional[TaskStatus] = None
    ) -> List[FollowUpTask]:
        query = """
            SELECT id, patient_id, title, status, due_date, owner, source_reference,
                   requires_human_confirmation, created_at, updated_at
            FROM follow_up_tasks
            WHERE patient_id = ?
        """
        params: list[Any] = [patient_id]
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at ASC;"

        async with self.db.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [
                FollowUpTask(
                    id=row["id"],
                    patient_id=row["patient_id"],
                    title=row["title"],
                    status=TaskStatus(row["status"]),
                    due_date=row["due_date"],
                    owner=row["owner"],
                    source_reference=row["source_reference"],
                    requires_human_confirmation=bool(row["requires_human_confirmation"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"]),
                )
                for row in rows
            ]

    async def create_task(self, task: FollowUpTask) -> FollowUpTask:
        async with transaction(self.db):
            await self.db.execute(
                """
                INSERT INTO follow_up_tasks (
                    id, patient_id, title, status, due_date, owner, source_reference,
                    requires_human_confirmation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task.id,
                    task.patient_id,
                    task.title,
                    task.status.value,
                    task.due_date,
                    task.owner,
                    task.source_reference,
                    1 if task.requires_human_confirmation else 0,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )
        return task

    # ---------------------------------------------------------
    # Task Proposal Operations
    # ---------------------------------------------------------
    async def get_proposal(self, proposal_id: str) -> Optional[TaskProposal]:
        async with self.db.execute(
            """
            SELECT id, patient_id, title, due_date, owner, source_reference,
                   status, proposed_by, reviewed_by, reviewed_at, created_at
            FROM task_proposals
            WHERE id = ?;
            """,
            (proposal_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return TaskProposal(
                id=row["id"],
                patient_id=row["patient_id"],
                title=row["title"],
                due_date=row["due_date"],
                owner=row["owner"],
                source_reference=row["source_reference"],
                status=ProposalStatus(row["status"]),
                proposed_by=row["proposed_by"],
                reviewed_by=row["reviewed_by"],
                reviewed_at=datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )

    async def create_proposal(self, proposal: TaskProposal) -> TaskProposal:
        async with transaction(self.db):
            await self.db.execute(
                """
                INSERT INTO task_proposals (
                    id, patient_id, title, due_date, owner, source_reference,
                    status, proposed_by, reviewed_by, reviewed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    proposal.id,
                    proposal.patient_id,
                    proposal.title,
                    proposal.due_date,
                    proposal.owner,
                    proposal.source_reference,
                    proposal.status.value,
                    proposal.proposed_by,
                    proposal.reviewed_by,
                    proposal.reviewed_at.isoformat() if proposal.reviewed_at else None,
                    proposal.created_at.isoformat(),
                ),
            )
        return proposal

    async def list_proposals(
        self, patient_id: str, status: Optional[ProposalStatus] = None
    ) -> list[TaskProposal]:
        query = """
            SELECT id, patient_id, title, due_date, owner, source_reference,
                   status, proposed_by, reviewed_by, reviewed_at, created_at
            FROM task_proposals
            WHERE patient_id = ?
        """
        params: list[Any] = [patient_id]
        if status:
            query += " AND status = ?"
            params.append(status.value)
        query += " ORDER BY created_at DESC;"

        async with self.db.execute(query, tuple(params)) as cursor:
            rows = await cursor.fetchall()
            return [
                TaskProposal(
                    id=row["id"],
                    patient_id=row["patient_id"],
                    title=row["title"],
                    due_date=row["due_date"],
                    owner=row["owner"],
                    source_reference=row["source_reference"],
                    status=ProposalStatus(row["status"]),
                    proposed_by=row["proposed_by"],
                    reviewed_by=row["reviewed_by"],
                    reviewed_at=datetime.fromisoformat(row["reviewed_at"]) if row["reviewed_at"] else None,
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in rows
            ]

    async def approve_proposal(
        self, proposal_id: str, approved_by: str
    ) -> FollowUpTask:
        """Atomically and idempotently approve a pending proposal, create the task, and log audit events."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' does not exist.")

        if proposal.status == ProposalStatus.REJECTED:
            raise ValueError(f"Cannot approve proposal '{proposal_id}' because it was already rejected.")

        # Idempotent retry: if already approved, return the exact task created for this proposal
        if proposal.status == ProposalStatus.APPROVED:
            async with self.db.execute(
                """
                SELECT details FROM audit_events
                WHERE action = ? AND entity_id = ?;
                """,
                (AuditAction.PROPOSAL_APPROVED.value, proposal.id),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    details = json.loads(row["details"])
                    task_id = details.get("created_task_id")
                    if task_id:
                        existing = await self.get_task(task_id)
                        if existing:
                            return existing

            # Fallback by exact title and patient
            async with self.db.execute(
                """
                SELECT id FROM follow_up_tasks
                WHERE patient_id = ? AND title = ?;
                """,
                (proposal.patient_id, proposal.title),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    existing_task = await self.get_task(row["id"])
                    if existing_task:
                        return existing_task

        now = datetime.now(timezone.utc)
        import uuid
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        requires_confirmation = (proposal.due_date is None or proposal.owner is None)
        task = FollowUpTask(
            id=task_id,
            patient_id=proposal.patient_id,
            title=proposal.title,
            status=TaskStatus.PENDING,
            due_date=proposal.due_date,
            owner=proposal.owner,
            source_reference=proposal.source_reference,
            requires_human_confirmation=requires_confirmation,
            created_at=now,
            updated_at=now,
        )

        audit_prop = AuditEvent(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            patient_id=proposal.patient_id,
            action=AuditAction.PROPOSAL_APPROVED,
            entity_type="proposal",
            entity_id=proposal.id,
            performed_by=approved_by,
            details={"approved_by": approved_by, "created_task_id": task.id},
            timestamp=now,
        )

        audit_task = AuditEvent(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            patient_id=proposal.patient_id,
            action=AuditAction.TASK_CREATED,
            entity_type="task",
            entity_id=task.id,
            performed_by=approved_by,
            details={"from_proposal_id": proposal.id, "title": task.title},
            timestamp=now,
        )

        async with transaction(self.db):
            # Concurrency check inside transaction lock
            async with self.db.execute(
                "SELECT status FROM task_proposals WHERE id = ?;", (proposal.id,)
            ) as lock_cur:
                row_status = await lock_cur.fetchone()
                if row_status and row_status["status"] == ProposalStatus.APPROVED.value:
                    async with self.db.execute(
                        "SELECT details FROM audit_events WHERE action = ? AND entity_id = ?;",
                        (AuditAction.PROPOSAL_APPROVED.value, proposal.id),
                    ) as c2:
                        r2 = await c2.fetchone()
                        if r2:
                            d2 = json.loads(r2["details"])
                            task_id_res = d2.get("created_task_id")
                            if task_id_res:
                                existing_res = await self.get_task(task_id_res)
                                if existing_res:
                                    return existing_res

            # 1. Atomic compare-and-swap update: only update if status is still PENDING
            cur = await self.db.execute(
                """
                UPDATE task_proposals
                SET status = ?, reviewed_by = ?, reviewed_at = ?
                WHERE id = ? AND status = 'PENDING';
                """,
                (
                    ProposalStatus.APPROVED.value,
                    approved_by,
                    now.isoformat(),
                    proposal.id,
                ),
            )
            if cur.rowcount == 0:
                # Concurrently approved by another process; return the already-created task
                async with self.db.execute(
                    "SELECT details FROM audit_events WHERE action = ? AND entity_id = ?;",
                    (AuditAction.PROPOSAL_APPROVED.value, proposal.id),
                ) as c_winner:
                    row_w = await c_winner.fetchone()
                    if row_w:
                        d_w = json.loads(row_w["details"])
                        tid = d_w.get("created_task_id")
                        if tid:
                            t_existing = await self.get_task(tid)
                            if t_existing:
                                return t_existing

                async with self.db.execute(
                    "SELECT id FROM follow_up_tasks WHERE patient_id = ? AND title = ?;",
                    (proposal.patient_id, proposal.title),
                ) as c_title:
                    row_t = await c_title.fetchone()
                    if row_t:
                        t_existing = await self.get_task(row_t["id"])
                        if t_existing:
                            return t_existing

            # 2. Insert follow-up task
            await self.db.execute(
                """
                INSERT INTO follow_up_tasks (
                    id, patient_id, title, status, due_date, owner, source_reference,
                    requires_human_confirmation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    task.id,
                    task.patient_id,
                    task.title,
                    task.status.value,
                    task.due_date,
                    task.owner,
                    task.source_reference,
                    1 if task.requires_human_confirmation else 0,
                    task.created_at.isoformat(),
                    task.updated_at.isoformat(),
                ),
            )
            # 3. Insert audit events
            await self.db.execute(
                """
                INSERT INTO audit_events (
                    id, patient_id, action, entity_type, entity_id, performed_by, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_prop.id,
                    audit_prop.patient_id,
                    audit_prop.action.value,
                    audit_prop.entity_type,
                    audit_prop.entity_id,
                    audit_prop.performed_by,
                    json.dumps(audit_prop.details),
                    audit_prop.timestamp.isoformat(),
                ),
            )
            await self.db.execute(
                """
                INSERT INTO audit_events (
                    id, patient_id, action, entity_type, entity_id, performed_by, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_task.id,
                    audit_task.patient_id,
                    audit_task.action.value,
                    audit_task.entity_type,
                    audit_task.entity_id,
                    audit_task.performed_by,
                    json.dumps(audit_task.details),
                    audit_task.timestamp.isoformat(),
                ),
            )

        return task

    async def reject_proposal(
        self, proposal_id: str, rejected_by: str, reason: str = "Rejected in simulator"
    ) -> TaskProposal:
        """Reject a pending proposal and log audit event."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal '{proposal_id}' does not exist.")
        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Cannot reject proposal '{proposal_id}' with status {proposal.status.value}.")

        now = datetime.now(timezone.utc)
        audit_event = AuditEvent(
            id=f"audit-{uuid.uuid4().hex[:8]}",
            patient_id=proposal.patient_id,
            action=AuditAction.PROPOSAL_REJECTED,
            entity_type="proposal",
            entity_id=proposal.id,
            performed_by=rejected_by,
            details={"rejection_reason": reason, "title": proposal.title},
            timestamp=now,
        )

        async with transaction(self.db):
            await self.db.execute(
                """
                UPDATE task_proposals
                SET status = ?, reviewed_by = ?, reviewed_at = ?
                WHERE id = ? AND status = 'PENDING';
                """,
                (
                    ProposalStatus.REJECTED.value,
                    rejected_by,
                    now.isoformat(),
                    proposal.id,
                ),
            )
            await self.db.execute(
                """
                INSERT INTO audit_events (
                    id, patient_id, action, entity_type, entity_id, performed_by, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    audit_event.id,
                    audit_event.patient_id,
                    audit_event.action.value,
                    audit_event.entity_type,
                    audit_event.entity_id,
                    audit_event.performed_by,
                    json.dumps(audit_event.details),
                    audit_event.timestamp.isoformat(),
                ),
            )

        updated = await self.get_proposal(proposal_id)
        return updated  # type: ignore

    # ---------------------------------------------------------
    # Audit Event Operations
    # ---------------------------------------------------------
    async def record_audit_event(self, event: AuditEvent) -> AuditEvent:
        # Enforce polymorphic referential integrity and patient isolation
        if event.entity_type == "task":
            async with self.db.execute(
                "SELECT patient_id FROM follow_up_tasks WHERE id = ?;", (event.entity_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Audit event references non-existent task '{event.entity_id}'.")
                if row["patient_id"] != event.patient_id:
                    raise ValueError(
                        f"Audit event patient '{event.patient_id}' does not match task patient '{row['patient_id']}'."
                    )
        elif event.entity_type == "proposal":
            async with self.db.execute(
                "SELECT patient_id FROM task_proposals WHERE id = ?;", (event.entity_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Audit event references non-existent proposal '{event.entity_id}'.")
                if row["patient_id"] != event.patient_id:
                    raise ValueError(
                        f"Audit event patient '{event.patient_id}' does not match proposal patient '{row['patient_id']}'."
                    )

        async with transaction(self.db):
            await self.db.execute(
                """
                INSERT INTO audit_events (
                    id, patient_id, action, entity_type, entity_id, performed_by, details, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    event.id,
                    event.patient_id,
                    event.action.value,
                    event.entity_type,
                    event.entity_id,
                    event.performed_by,
                    json.dumps(event.details),
                    event.timestamp.isoformat(),
                ),
            )
        return event

    async def list_audit_events(self, patient_id: str) -> List[AuditEvent]:
        async with self.db.execute(
            """
            SELECT id, patient_id, action, entity_type, entity_id, performed_by, details, timestamp
            FROM audit_events
            WHERE patient_id = ?
            ORDER BY timestamp ASC;
            """,
            (patient_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                AuditEvent(
                    id=row["id"],
                    patient_id=row["patient_id"],
                    action=AuditAction(row["action"]),
                    entity_type=row["entity_type"],
                    entity_id=row["entity_id"],
                    performed_by=row["performed_by"],
                    details=json.loads(row["details"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                )
                for row in rows
            ]
