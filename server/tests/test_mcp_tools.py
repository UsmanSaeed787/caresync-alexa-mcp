"""Integration tests for the 5 CareSync MCP tools."""

import aiosqlite
import pytest

from src.data.seeder import seed_synthetic_data
from src.db.repository import CareSyncRepository
from src.mcp.tools import (
    tool_approve_follow_up_task,
    tool_get_audit_log,
    tool_get_discharge_plan,
    tool_list_follow_up_tasks,
    tool_propose_follow_up_task,
)


@pytest.fixture(autouse=True)
async def seed_data(test_db_path: str) -> None:
    await seed_synthetic_data(db_path_override=test_db_path)


async def test_mcp_get_discharge_plan(test_db_path: str) -> None:
    """Verify tool_get_discharge_plan returns synthetic plan and source excerpts."""
    plan = await tool_get_discharge_plan("patient-synthetic-001", db_path_override=test_db_path)
    assert plan["patient_id"] == "patient-synthetic-001"
    assert plan["is_synthetic"] is True
    assert len(plan["source_excerpts"]) >= 3
    assert "cardiology_follow_up_date" in plan["explicit_missing_fields"]
    assert "Eleanor Vance [SYNTHETIC]" in plan["source_text"]


async def test_mcp_get_discharge_plan_rejects_non_synthetic(test_db_path: str) -> None:
    """Non-synthetic IDs must be rejected."""
    with pytest.raises(ValueError) as exc:
        await tool_get_discharge_plan("real-patient-999", db_path_override=test_db_path)
    assert "Only synthetic patient IDs are allowed" in str(exc.value)


async def test_mcp_list_tasks_and_filter(test_db_path: str) -> None:
    """Verify list_follow_up_tasks preserves nulls and filters properly."""
    tasks = await tool_list_follow_up_tasks("patient-synthetic-001", db_path_override=test_db_path)
    assert len(tasks) == 3

    # Check unassigned task preserves explicit nulls
    unassigned = next(t for t in tasks if t["id"] == "task-synth-003")
    assert unassigned["due_date"] is None
    assert unassigned["owner"] is None
    assert unassigned["requires_human_confirmation"] is True

    # Filter by COMPLETED
    completed = await tool_list_follow_up_tasks(
        "patient-synthetic-001", status="COMPLETED", db_path_override=test_db_path
    )
    assert len(completed) == 1
    assert completed[0]["status"] == "COMPLETED"


async def test_mcp_propose_task_valid_source_reference(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Proposing a task with valid source text creates a PENDING proposal without creating an approved task."""
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    title = "Follow-up consultation with Dr. Sarah Jenkins"

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title=title,
        due_date="2026-10-27",
        owner=None,  # explicitly null
        db_path_override=test_db_path,
    )

    assert prop["proposal_id"].startswith("proposal-")
    assert prop["status"] == "PENDING"
    assert prop["due_date"] == "2026-10-27"
    assert prop["owner"] is None

    # Verify NO approved task was created in follow_up_tasks with this title
    repo = CareSyncRepository(test_db_conn)
    current_tasks = await repo.list_tasks("patient-synthetic-001")
    matching_tasks = [t for t in current_tasks if t.title == title]
    assert len(matching_tasks) == 0, "Unapproved proposals must not appear as persisted tasks"

    # Verify audit event recorded for proposal creation
    events = await repo.list_audit_events("patient-synthetic-001")
    prop_events = [e for e in events if e.entity_id == prop["proposal_id"]]
    assert len(prop_events) == 1
    assert prop_events[0].action.value == "PROPOSAL_CREATED"


async def test_mcp_propose_task_rejects_fabricated_source_reference(test_db_path: str) -> None:
    """Proposing task with unsupported or hallucinated source reference must fail validation."""
    with pytest.raises(ValueError) as exc:
        await tool_propose_follow_up_task(
            patient_id="patient-synthetic-001",
            source_reference="Prescribe 100mg of new investigational drug daily",
            title="Investigational drug prescription",
            db_path_override=test_db_path,
        )
    assert "could not be verified against the patient's discharge plan" in str(exc.value)


async def test_mcp_approve_proposal_creates_task_and_audit(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Approving a pending proposal atomically persists the task and records audit events."""
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    title = "Approved PCP Consultation"

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title=title,
        due_date="2026-10-27",
        owner="Care Coordinator Alex",
        db_path_override=test_db_path,
    )

    approval_res = await tool_approve_follow_up_task(
        proposal_id=prop["proposal_id"],
        approved_by="Care Coordinator Alex",
        db_path_override=test_db_path,
    )

    assert approval_res["status"] == "APPROVED"
    assert approval_res["task"]["title"] == title
    assert approval_res["task"]["owner"] == "Care Coordinator Alex"

    # Verify task is now actively persisted in database
    repo = CareSyncRepository(test_db_conn)
    persisted_task = await repo.get_task(approval_res["task"]["id"])
    assert persisted_task is not None
    assert persisted_task.title == title

    # Verify proposal status was updated
    proposal_in_db = await repo.get_proposal(prop["proposal_id"])
    assert proposal_in_db is not None
    assert proposal_in_db.status.value == "APPROVED"
    assert proposal_in_db.reviewed_by == "Care Coordinator Alex"
    assert proposal_in_db.reviewed_at is not None

    # Verify audit events for both proposal approval and task creation
    audit_events = await repo.list_audit_events("patient-synthetic-001")
    actions = [e.action.value for e in audit_events]
    assert "PROPOSAL_APPROVED" in actions
    assert "TASK_CREATED" in actions


async def test_mcp_approve_proposal_idempotent_retry(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Repeated approval calls must not duplicate tasks or audit events."""
    excerpt = "Follow up with outpatient cardiology clinic. Patient requires echocardiogram in 4 weeks."
    title = "Idempotent Cardiology Task"

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title=title,
        db_path_override=test_db_path,
    )

    # First approval
    res1 = await tool_approve_follow_up_task(
        proposal_id=prop["proposal_id"],
        approved_by="Care Coordinator Alex",
        db_path_override=test_db_path,
    )
    first_task_id = res1["task"]["id"]

    # Second approval (retry)
    res2 = await tool_approve_follow_up_task(
        proposal_id=prop["proposal_id"],
        approved_by="Care Coordinator Alex",
        db_path_override=test_db_path,
    )
    assert res2["task"]["id"] == first_task_id, "Repeated approval must return existing task"

    # Verify count of tasks matching this title in DB is strictly 1
    repo = CareSyncRepository(test_db_conn)
    tasks = await repo.list_tasks("patient-synthetic-001")
    matching = [t for t in tasks if t.title == title]
    assert len(matching) == 1, "There must be exactly 1 task created, no duplicates"


async def test_mcp_approve_rejects_invalid_id(test_db_path: str) -> None:
    """Attempting to approve a non-existent proposal ID must return a descriptive error."""
    with pytest.raises(ValueError) as exc:
        await tool_approve_follow_up_task(
            proposal_id="proposal-nonexistent-12345",
            approved_by="Care Coordinator Alex",
            db_path_override=test_db_path,
        )
    assert "does not exist" in str(exc.value)


async def test_mcp_get_audit_log(test_db_path: str) -> None:
    """Verify tool_get_audit_log returns full event trail."""
    excerpt = "Order basic metabolic panel (BMP) in 10-14 days to monitor renal function after furosemide adjustment."
    await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title="BMP Lab Work",
        db_path_override=test_db_path,
    )

    log = await tool_get_audit_log("patient-synthetic-001", db_path_override=test_db_path)
    assert len(log) >= 1
    assert any(e["action"] == "PROPOSAL_CREATED" for e in log)


async def test_mcp_approve_proposal_concurrent_attempts(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Concurrent approval requests for the same proposal must not produce duplicate tasks or events."""
    import asyncio
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    title = "Concurrent Approval Task"

    prop = await tool_propose_follow_up_task(
        patient_id="patient-synthetic-001",
        source_reference=excerpt,
        title=title,
        db_path_override=test_db_path,
    )

    # Launch two approvals concurrently
    results = await asyncio.gather(
        tool_approve_follow_up_task(prop["proposal_id"], "Coordinator A", db_path_override=test_db_path),
        tool_approve_follow_up_task(prop["proposal_id"], "Coordinator B", db_path_override=test_db_path),
        return_exceptions=True,
    )

    valid_tasks = [r["task"]["id"] for r in results if isinstance(r, dict) and "task" in r]
    assert len(valid_tasks) == 2, "Both concurrent approval calls must resolve successfully"
    assert valid_tasks[0] == valid_tasks[1], "Both concurrent calls must reference the exact same task ID"

    # Verify only 1 task in database
    repo = CareSyncRepository(test_db_conn)
    tasks = await repo.list_tasks("patient-synthetic-001")
    matching = [t for t in tasks if t.title == title]
    assert len(matching) == 1, "Concurrent approval must not create duplicate tasks"

