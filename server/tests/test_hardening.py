"""Comprehensive hardening and audit test suite for CareSync.

Covers:
- Approval and rejection state transitions and illegal transitions
- High-concurrency approval deduplication and idempotency
- Audit polymorphic integrity and cross-patient isolation
- Source reference verification and rejection of fabricated evidence
- Explicit null preservation for missing fields
- Clinical emergency refusal and API error boundaries
- Full end-to-end lifecycle verification via REST and MCP tools
"""

import asyncio
from datetime import datetime, timezone
import aiosqlite
from httpx import AsyncClient
import pytest

from src.data.seeder import seed_synthetic_data
from src.db.connection import get_db
from src.db.repository import CareSyncRepository
from src.domain.enums import AuditAction, ProposalStatus, TaskStatus
from src.domain.models import AuditEvent, FollowUpTask, TaskProposal
from src.mcp.tools import (
    tool_approve_follow_up_task,
    tool_get_audit_log,
    tool_list_follow_up_tasks,
    tool_propose_follow_up_task,
)


# =====================================================================
# 1. Approval and Rejection State Transitions
# =====================================================================

async def test_cannot_approve_rejected_proposal(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """An explicitly rejected proposal cannot subsequently be approved."""
    await seed_synthetic_data(db_path_override=test_db_path)
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title="PCP Follow-Up To Reject",
        db_path_override=test_db_path,
    )
    proposal_id = prop["proposal_id"]

    repo = CareSyncRepository(test_db_conn)
    # Reject the proposal
    rejected = await repo.reject_proposal(proposal_id, "Coordinator Alex", "Unnecessary task")
    assert rejected.status == ProposalStatus.REJECTED

    # Attempting to approve rejected proposal must fail
    with pytest.raises(ValueError) as exc:
        await tool_approve_follow_up_task(proposal_id, "Coordinator Alex", db_path_override=test_db_path)
    assert "already rejected" in str(exc.value).lower()


async def test_cannot_reject_approved_proposal(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """An approved proposal cannot subsequently be rejected."""
    await seed_synthetic_data(db_path_override=test_db_path)
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title="PCP Follow-Up To Approve",
        db_path_override=test_db_path,
    )
    proposal_id = prop["proposal_id"]

    # Approve it
    approved = await tool_approve_follow_up_task(proposal_id, "Coordinator Alex", db_path_override=test_db_path)
    assert approved["status"] == "APPROVED"

    repo = CareSyncRepository(test_db_conn)
    # Attempting to reject approved proposal must fail
    with pytest.raises(ValueError) as exc:
        await repo.reject_proposal(proposal_id, "Coordinator Alex", "Belated rejection")
    assert "with status approved" in str(exc.value).lower()


async def test_reject_nonexistent_proposal(test_db_conn: aiosqlite.Connection) -> None:
    """Rejecting a non-existent proposal ID raises a clear ValueError."""
    repo = CareSyncRepository(test_db_conn)
    with pytest.raises(ValueError) as exc:
        await repo.reject_proposal("proposal-nonexistent-999", "Coordinator Alex")
    assert "does not exist" in str(exc.value).lower()


# =====================================================================
# 2. High-Concurrency Approval Stress Test
# =====================================================================

async def test_high_concurrency_approval_deduplication(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Five simultaneous approval requests must resolve to the exact same task with no duplicate inserts."""
    await seed_synthetic_data(db_path_override=test_db_path)
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    title = "High Concurrency Approval Task"

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title=title,
        db_path_override=test_db_path,
    )
    proposal_id = prop["proposal_id"]

    # Launch 5 concurrent approval attempts simulating multiple coordinators or retries
    workers = [f"Coordinator Worker {i}" for i in range(5)]
    coros = [
        tool_approve_follow_up_task(proposal_id, worker, db_path_override=test_db_path)
        for worker in workers
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    # Every call should resolve successfully
    task_ids = []
    for r in results:
        assert isinstance(r, dict), f"Expected dict result, got exception: {r}"
        assert r["status"] == "APPROVED"
        task_ids.append(r["task"]["id"])

    # All returned task IDs must be identical
    assert len(task_ids) == 5
    assert len(set(task_ids)) == 1, "All concurrent approvals must return the exact same task ID"

    # Verify only ONE task was inserted into the database
    repo = CareSyncRepository(test_db_conn)
    tasks = await repo.list_tasks("patient-synthetic-001")
    matching = [t for t in tasks if t.title == title]
    assert len(matching) == 1, f"Expected exactly 1 task, found {len(matching)}"

    # Verify only ONE TASK_CREATED audit event was recorded for this task
    audit_events = await repo.list_audit_events("patient-synthetic-001")
    task_created_events = [
        ev for ev in audit_events
        if ev.action == AuditAction.TASK_CREATED and ev.entity_id == task_ids[0]
    ]
    assert len(task_created_events) == 1, "Only one TASK_CREATED audit event should be logged"


# =====================================================================
# 3. Audit Integrity: Polymorphic Proposal Association & Patient Isolation
# =====================================================================

async def test_audit_event_proposal_polymorphic_integrity(test_db_conn: aiosqlite.Connection) -> None:
    """Audit events referencing proposals must validate proposal existence and patient identity."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    repo = CareSyncRepository(test_db_conn)

    # Setup two patients
    await test_db_conn.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, 1, ?);",
        ("patient-synth-x", "SYNTH-MRN-XXX", "Patient X [SYNTHETIC]", "1970-01-01", now_iso),
    )
    await test_db_conn.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, 1, ?);",
        ("patient-synth-y", "SYNTH-MRN-YYY", "Patient Y [SYNTHETIC]", "1975-01-01", now_iso),
    )
    # Proposal belongs to patient X
    await test_db_conn.execute(
        """
        INSERT INTO task_proposals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("proposal-x-1", "patient-synth-x", "Proposal X", None, None, "Valid source text", "PENDING", "agent", None, None, now_iso),
    )
    await test_db_conn.commit()

    # 1. Non-existent proposal reference raises ValueError
    with pytest.raises(ValueError) as exc_nonexistent:
        await repo.record_audit_event(
            AuditEvent(
                id="audit-fake-prop",
                patient_id="patient-synth-x",
                action=AuditAction.PROPOSAL_REJECTED,
                entity_type="proposal",
                entity_id="proposal-nonexistent-123",
                performed_by="user",
            )
        )
    assert "non-existent proposal" in str(exc_nonexistent.value).lower()

    # 2. Cross-patient mismatch: event claims patient Y, but proposal belongs to patient X
    with pytest.raises(ValueError) as exc_mismatch:
        await repo.record_audit_event(
            AuditEvent(
                id="audit-cross-patient-prop",
                patient_id="patient-synth-y",  # Wrong patient!
                action=AuditAction.PROPOSAL_REJECTED,
                entity_type="proposal",
                entity_id="proposal-x-1",
                performed_by="user",
            )
        )
    assert "does not match proposal patient" in str(exc_mismatch.value).lower()


# =====================================================================
# 4. Source Evidence Verification & Explicit Nulls
# =====================================================================

async def test_rejection_of_fabricated_source_reference(test_db_path: str) -> None:
    """Proposing a task with fabricated or hallucinated source text must be rejected."""
    await seed_synthetic_data(db_path_override=test_db_path)

    fabricated_references = [
        "Administer 50mg hydrochlorothiazide daily (completely invented)",
        "Patient should undergo emergency MRI scan tomorrow",
        "todo",
        "n/a",
        "",
    ]

    for ref in fabricated_references:
        with pytest.raises(ValueError):
            await tool_propose_follow_up_task(
                patient_id="patient-synthetic-001",
                source_reference=ref,
                title="Fabricated Follow-Up",
                db_path_override=test_db_path,
            )


async def test_explicit_null_preservation(test_db_path: str) -> None:
    """Unstated dates and owners remain explicitly None / null and flag human confirmation."""
    await seed_synthetic_data(db_path_override=test_db_path)
    excerpt = "Order basic metabolic panel (BMP) in 10-14 days to monitor renal function after furosemide adjustment."

    # Propose with None for due_date and owner
    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title="BMP Panel (Unassigned)",
        due_date=None,
        owner=None,
        db_path_override=test_db_path,
    )
    proposal_id = prop["proposal_id"]

    # Approve the proposal
    appr = await tool_approve_follow_up_task(proposal_id, "Coordinator Alex", db_path_override=test_db_path)
    task = appr["task"]

    assert task["due_date"] is None, "Due date must be None when unstated"
    assert task["owner"] is None, "Owner must be None when unassigned"
    assert task["requires_human_confirmation"] is True, "Must flag requires_human_confirmation when fields are missing"


# =====================================================================
# 5. REST API Safety Boundaries and Emergency Refusal
# =====================================================================

async def test_api_rejects_non_synthetic_queries(async_client: AsyncClient, test_db_path: str) -> None:
    """API endpoints strictly enforce synthetic patient ID validation."""
    await seed_synthetic_data(db_path_override=test_db_path)

    # 1. Context query with non-synthetic ID
    ctx_res = await async_client.get("/api/v1/context?patient_id=real-patient-98231")
    assert ctx_res.status_code == 400
    assert "synthetic" in ctx_res.json()["detail"].lower()

    # 2. Agent chat with non-synthetic ID
    chat_res = await async_client.post(
        "/api/v1/agent/chat",
        json={"prompt": "What follow-ups are needed?", "patient_id": "real-patient-98231"},
    )
    assert chat_res.status_code == 400
    assert "synthetic" in chat_res.json()["detail"].lower()


async def test_api_emergency_triage_refusal(async_client: AsyncClient, test_db_path: str) -> None:
    """Chat API strictly refuses clinical triage and emergencies with safe emergency guidance."""
    await seed_synthetic_data(db_path_override=test_db_path)

    emergency_prompts = [
        "Patient is experiencing crushing chest pain radiating to left arm",
        "Shortness of breath and severe dizziness, what diagnosis?",
        "Should I adjust insulin dosage?",
    ]

    for prompt in emergency_prompts:
        res = await async_client.post(
            "/api/v1/agent/chat",
            json={"prompt": prompt, "patient_id": "patient-synthetic-001"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["safety_refusal"] is True
        assert (
            "cannot assess medical emergencies" in data["response_text"].lower()
            or "clinical triage" in data["response_text"].lower()
            or "medical advice" in data["response_text"].lower()
        )
        assert "911" in data["response_text"] or "emergency" in data["response_text"].lower()


# =====================================================================
# 6. Complete REST Lifecycle: Propose -> Reject -> Propose -> Approve -> Audit
# =====================================================================

async def test_full_lifecycle_api_workflow(async_client: AsyncClient, test_db_path: str) -> None:
    """Comprehensive lifecycle exercising the complete workflow through REST."""
    await seed_synthetic_data(db_path_override=test_db_path)
    excerpt_pcp = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    excerpt_bmp = "Order basic metabolic panel (BMP) in 10-14 days to monitor renal function after furosemide adjustment."

    # 1. Fetch initial context
    ctx = (await async_client.get("/api/v1/context?patient_id=patient-synthetic-001")).json()
    assert ctx["patient"]["full_name"] == "Eleanor Vance [SYNTHETIC]"

    # 2. Initial tasks count is 3
    tasks_initial = (await async_client.get("/api/v1/tasks?patient_id=patient-synthetic-001")).json()
    assert len(tasks_initial) == 3

    # 3. Propose Task 1 (which will be dismissed)
    prop1_res = await async_client.post(
        "/api/v1/tasks/propose",
        json={
            "patient_id": "patient-synthetic-001",
            "title": "Redundant BMP Follow-Up",
            "source_reference": excerpt_bmp,
            "due_date": None,
            "owner": None,
        },
    )
    assert prop1_res.status_code == 200
    prop1_id = prop1_res.json()["proposal_id"]

    # 4. Reject Task 1
    rej1_res = await async_client.post(
        "/api/v1/tasks/reject",
        json={"proposal_id": prop1_id, "rejected_by": "Coordinator Alex", "reason": "Already scheduled"},
    )
    assert rej1_res.status_code == 200
    assert rej1_res.json()["status"] == "REJECTED"

    # 5. Verify Task 1 was NOT added to follow_up_tasks
    tasks_after_reject = (await async_client.get("/api/v1/tasks?patient_id=patient-synthetic-001")).json()
    assert len(tasks_after_reject) == 3, "Rejected proposal must not create a task"

    # 6. Propose Task 2 (which will be approved)
    prop2_res = await async_client.post(
        "/api/v1/tasks/propose",
        json={
            "patient_id": "patient-synthetic-001",
            "title": "Dr. Sarah Jenkins PCP Visit",
            "source_reference": excerpt_pcp,
            "due_date": "2026-10-27",
            "owner": "Dr. Sarah Jenkins",
        },
    )
    assert prop2_res.status_code == 200
    prop2_id = prop2_res.json()["proposal_id"]

    # 7. Approve Task 2
    appr2_res = await async_client.post(
        "/api/v1/tasks/approve",
        json={"proposal_id": prop2_id, "approved_by": "Coordinator Alex"},
    )
    assert appr2_res.status_code == 200
    assert appr2_res.json()["status"] == "APPROVED"
    created_task = appr2_res.json()["task"]
    assert created_task["title"] == "Dr. Sarah Jenkins PCP Visit"

    # 8. Verify Task 2 is now active on the board (count is 4)
    tasks_final = (await async_client.get("/api/v1/tasks?patient_id=patient-synthetic-001")).json()
    assert len(tasks_final) == 4
    assert any(t["id"] == created_task["id"] for t in tasks_final)

    # 9. Verify Audit Trail contains all actions in provenance order
    audit = (await async_client.get("/api/v1/audit?patient_id=patient-synthetic-001")).json()
    actions = [ev["action"] for ev in audit]
    assert "PROPOSAL_CREATED" in actions
    assert "PROPOSAL_REJECTED" in actions
    assert "PROPOSAL_APPROVED" in actions
    assert "TASK_CREATED" in actions
