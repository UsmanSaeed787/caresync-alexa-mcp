"""Unit tests for domain models, boundary enforcement, and explicit nullability."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from src.domain.enums import AuditAction, ProposalStatus, TaskStatus
from src.domain.models import AuditEvent, DischargePlan, FollowUpTask, Patient, TaskProposal


def test_patient_model_valid() -> None:
    p = Patient(
        id="patient-synthetic-001",
        mrn="SYNTH-MRN-84920",
        full_name="Eleanor Vance [SYNTHETIC]",
        date_of_birth="1952-08-14",
        is_synthetic=True,
    )
    assert p.id == "patient-synthetic-001"
    assert p.mrn.startswith("SYNTH-")
    assert p.is_synthetic is True


def test_patient_model_rejects_non_synthetic_mrn() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Patient(
            id="patient-1",
            mrn="REAL-MRN-9999",
            full_name="Real Patient [SYNTHETIC]",
            date_of_birth="1970-01-01",
            is_synthetic=True,
        )
    assert "MRN must begin with 'SYNTH-'" in str(exc_info.value)


def test_patient_model_rejects_missing_synthetic_name_tag() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Patient(
            id="patient-1",
            mrn="SYNTH-MRN-123",
            full_name="Eleanor Vance",
            date_of_birth="1952-08-14",
            is_synthetic=True,
        )
    assert "must explicitly include '[SYNTHETIC]'" in str(exc_info.value)


def test_follow_up_task_explicit_nulls() -> None:
    task = FollowUpTask(
        id="task-001",
        patient_id="patient-synthetic-001",
        title="Schedule cardiology follow-up",
        status=TaskStatus.PENDING,
        due_date=None,
        owner=None,
        source_reference="Cardiology follow-up in 4 weeks requested in discharge instructions.",
        requires_human_confirmation=True,
    )
    assert task.due_date is None, "Missing due dates must remain explicitly None"
    assert task.owner is None, "Missing owners must remain explicitly None"
    assert task.requires_human_confirmation is True


def test_follow_up_task_rejects_invalid_source_reference() -> None:
    # 1. Too short
    with pytest.raises(ValidationError):
        FollowUpTask(
            id="task-001",
            patient_id="patient-synthetic-001",
            title="Invalid Task",
            status=TaskStatus.PENDING,
            source_reference="N/A",
        )

    # 2. Placeholder text
    with pytest.raises(ValidationError) as exc_info:
        FollowUpTask(
            id="task-002",
            patient_id="patient-synthetic-001",
            title="Invalid Task",
            status=TaskStatus.PENDING,
            source_reference="None ",
        )
    assert "source_reference must cite a valid excerpt" in str(exc_info.value)


def test_proposal_review_consistency_pending() -> None:
    # Valid pending proposal
    prop = TaskProposal(
        id="prop-001",
        patient_id="patient-synthetic-001",
        title="Proposed appointment",
        source_reference="Follow up with primary care physician within 7 days.",
        status=ProposalStatus.PENDING,
        proposed_by="agent-alexa-simulator",
    )
    assert prop.reviewed_by is None
    assert prop.reviewed_at is None

    # Invalid: pending with reviewed_by set
    with pytest.raises(ValidationError) as exc_info:
        TaskProposal(
            id="prop-002",
            patient_id="patient-synthetic-001",
            title="Proposed appointment",
            source_reference="Follow up with primary care physician within 7 days.",
            status=ProposalStatus.PENDING,
            proposed_by="agent-alexa-simulator",
            reviewed_by="Coordinator",
        )
    assert "Pending proposals must have null reviewed_by" in str(exc_info.value)


def test_proposal_review_consistency_approved() -> None:
    now = datetime.now(timezone.utc)
    # Valid approved proposal
    prop = TaskProposal(
        id="prop-003",
        patient_id="patient-synthetic-001",
        title="Proposed appointment",
        source_reference="Follow up with primary care physician within 7 days.",
        status=ProposalStatus.APPROVED,
        proposed_by="agent-alexa-simulator",
        reviewed_by="Coordinator Alex",
        reviewed_at=now,
    )
    assert prop.status == ProposalStatus.APPROVED
    assert prop.reviewed_by == "Coordinator Alex"

    # Invalid: approved without reviewer
    with pytest.raises(ValidationError) as exc_info:
        TaskProposal(
            id="prop-004",
            patient_id="patient-synthetic-001",
            title="Proposed appointment",
            source_reference="Follow up with primary care physician within 7 days.",
            status=ProposalStatus.APPROVED,
            proposed_by="agent-alexa-simulator",
        )
    assert "Approved or Rejected proposals must specify reviewed_by" in str(exc_info.value)


def test_audit_event_creation() -> None:
    event = AuditEvent(
        id="audit-001",
        patient_id="patient-synthetic-001",
        action=AuditAction.PROPOSAL_CREATED,
        entity_type="proposal",
        entity_id="prop-001",
        performed_by="care-coordinator",
        details={"field": "due_date", "new_value": "2026-10-27"},
    )
    assert event.action == AuditAction.PROPOSAL_CREATED
    assert event.entity_type == "proposal"


def test_source_reference_validation_against_plan() -> None:
    from src.domain.source_validator import validate_source_reference

    plan = DischargePlan(
        id="plan-test-001",
        patient_id="patient-synthetic-001",
        admission_date="2026-10-14",
        discharge_date="2026-10-20",
        summary="Test summary",
        source_text="Follow up with Dr. Sarah Jenkins within 7 days. Patient needs echocardiogram in 4 weeks.",
        source_excerpts=[
            {
                "category": "PCP Follow-Up",
                "text": "Follow up with Dr. Sarah Jenkins within 7 days.",
            },
            {
                "category": "Cardiology",
                "text": "Patient needs echocardiogram in 4 weeks.",
            },
        ],
        explicit_missing_fields=["cardiology_follow_up_date"],
    )

    # Valid matches
    assert validate_source_reference("Dr. Sarah Jenkins", plan) is True
    assert validate_source_reference("echocardiogram in 4 weeks", plan) is True
    assert validate_source_reference("PCP Follow-Up", plan) is True
    assert validate_source_reference("cardiology_follow_up_date", plan) is True

    # Fabricated / unsupported references
    assert validate_source_reference("Follow up with orthopedics tomorrow", plan) is False
    assert validate_source_reference("Prescribe 50mg hydrochlorothiazide", plan) is False
    assert validate_source_reference("N/A", plan) is False
    assert validate_source_reference("", plan) is False

