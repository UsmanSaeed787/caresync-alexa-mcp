"""Tests for the deterministic CareSync agent adapter driving the golden-path demo."""

import pytest

from src.agent.adapter import DeterministicAgentAdapter
from src.data.seeder import seed_synthetic_data


@pytest.fixture(autouse=True)
async def seed_data(test_db_path: str) -> None:
    await seed_synthetic_data(db_path_override=test_db_path)


async def test_agent_inquire_outstanding_tasks() -> None:
    """Agent answers 'What follow-ups are still outstanding?' by calling MCP tools."""
    adapter = DeterministicAgentAdapter()
    result = await adapter.process_user_turn(
        prompt="What follow-ups are still outstanding?",
        patient_id="patient-synthetic-001",
    )

    assert len(result.tool_calls) == 2
    tool_names = [tc.tool for tc in result.tool_calls]
    assert "get_discharge_plan" in tool_names
    assert "list_follow_up_tasks" in tool_names

    # Verify structured synthesis cites Eleanor Vance, pending tasks, and explicit missing fields
    assert "Eleanor Vance" in result.response_text
    assert "Outstanding (Pending) Tasks" in result.response_text
    assert "cardiology_follow_up_date" in result.response_text
    assert result.pending_proposal is None


async def test_agent_prepare_follow_up_task() -> None:
    """Agent prepares a follow-up proposal for PCP appointment and keeps it pending human approval."""
    adapter = DeterministicAgentAdapter()
    result = await adapter.process_user_turn(
        prompt="Prepare a follow-up task for the primary-care appointment",
        patient_id="patient-synthetic-001",
    )

    assert len(result.tool_calls) == 2
    tool_names = [tc.tool for tc in result.tool_calls]
    assert "get_discharge_plan" in tool_names
    assert "propose_follow_up_task" in tool_names

    assert result.pending_proposal is not None
    assert result.pending_proposal["status"] == "PENDING"
    assert result.pending_proposal["due_date"] == "2026-10-27"
    assert "pending approval" in result.response_text.lower()


async def test_agent_approve_follow_up_task() -> None:
    """Agent executes approval tool when coordinator instructs to approve."""
    adapter = DeterministicAgentAdapter()
    # Step 1: Prepare proposal
    prep_result = await adapter.process_user_turn(
        prompt="Prepare a follow-up task for the primary-care appointment",
        patient_id="patient-synthetic-001",
    )
    prop_id = prep_result.pending_proposal["proposal_id"]

    # Step 2: Approve proposal
    appr_result = await adapter.process_user_turn(
        prompt=f"Approve proposal {prop_id}",
        patient_id="patient-synthetic-001",
    )

    assert len(appr_result.tool_calls) == 1
    assert appr_result.tool_calls[0].tool == "approve_follow_up_task"
    assert "approved by Care Coordinator Alex" in appr_result.response_text


async def test_agent_audit_log_inquiry() -> None:
    """Agent answers audit log inquiry by retrieving the immutable audit trail."""
    adapter = DeterministicAgentAdapter()
    result = await adapter.process_user_turn(
        prompt="Show audit trail and recent changes",
        patient_id="patient-synthetic-001",
    )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool == "get_audit_log"
    assert "Audit trail for synthetic patient" in result.response_text


async def test_agent_clinical_triage_refusal() -> None:
    """Agent refuses clinical triage, diagnosis, and emergency assessment."""
    adapter = DeterministicAgentAdapter()
    result = await adapter.process_user_turn(
        prompt="The patient has severe chest pain and needs a medication change",
        patient_id="patient-synthetic-001",
    )

    assert len(result.tool_calls) == 0, "No clinical tools should be called on emergency prompts"
    assert "CRITICAL SAFETY NOTICE" in result.response_text
    assert "emergency services" in result.response_text
