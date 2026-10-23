"""CareSync Pydantic domain models with strict boundary enforcement and explicit nullability."""

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.enums import AuditAction, ProposalStatus, TaskStatus


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Patient(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique patient identifier")
    mrn: str = Field(..., description="Medical Record Number, must begin with SYNTH-")
    full_name: str = Field(..., description="Fictional patient full name")
    date_of_birth: str = Field(..., description="Date of birth in YYYY-MM-DD format")
    is_synthetic: Literal[True] = Field(
        default=True,
        description="Permanent safety invariant: must always be True"
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("mrn")
    @classmethod
    def validate_mrn_synthetic(cls, v: str) -> str:
        if not v or not v.startswith("SYNTH-"):
            raise ValueError("All patients must be synthetic; MRN must begin with 'SYNTH-'")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_name_synthetic(cls, v: str) -> str:
        if "[SYNTHETIC]" not in v and "SYNTHETIC" not in v.upper():
            raise ValueError("Patient full name must explicitly include '[SYNTHETIC]' label")
        return v


class DischargePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique plan identifier")
    patient_id: str = Field(..., description="Reference to patient ID")
    admission_date: str = Field(..., description="Admission date YYYY-MM-DD (fictional scenario)")
    discharge_date: str = Field(..., description="Discharge date YYYY-MM-DD (fictional scenario)")
    summary: str = Field(..., description="Discharge summary overview")
    source_text: str = Field(..., description="Verbatim synthetic discharge instructions")
    source_excerpts: list[dict[str, str]] = Field(
        default_factory=list,
        description="Keyed verbatim excerpts supporting follow-up requirements"
    )
    explicit_missing_fields: list[str] = Field(
        default_factory=list,
        description="Fields explicitly absent from the discharge plan"
    )
    created_at: datetime = Field(default_factory=_utc_now)


class FollowUpTask(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(..., description="Unique task identifier")
    patient_id: str = Field(..., description="Reference to patient ID")
    title: str = Field(..., min_length=3, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    due_date: Optional[str] = Field(
        default=None,
        description="Due date in YYYY-MM-DD format; explicit None if not specified"
    )
    owner: Optional[str] = Field(
        default=None,
        description="Assigned role/person; explicit None if unassigned"
    )
    source_reference: str = Field(
        ...,
        min_length=5,
        description="Verbatim excerpt or section title justifying this task"
    )
    requires_human_confirmation: bool = Field(
        default=False,
        description="True if dates/owners or details were missing and require human confirmation"
    )
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    @field_validator("source_reference")
    @classmethod
    def validate_source_ref(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned or cleaned.lower() in {"none", "n/a", "null", "test", "todo"}:
            raise ValueError("source_reference must cite a valid excerpt or section from the discharge plan")
        return cleaned


class TaskProposal(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str = Field(..., description="Unique proposal identifier")
    patient_id: str = Field(..., description="Reference to patient ID")
    title: str = Field(..., min_length=3, description="Proposed task title")
    due_date: Optional[str] = Field(
        default=None,
        description="Proposed due date; None if unstated in source"
    )
    owner: Optional[str] = Field(
        default=None,
        description="Proposed owner; None if unassigned in source"
    )
    source_reference: str = Field(
        ...,
        min_length=5,
        description="Verbatim excerpt or section supporting this proposal"
    )
    status: ProposalStatus = Field(default=ProposalStatus.PENDING)
    proposed_by: str = Field(..., description="Agent or user identifier that generated the proposal")
    reviewed_by: Optional[str] = Field(
        default=None,
        description="User who approved or rejected the proposal"
    )
    reviewed_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of review"
    )
    created_at: datetime = Field(default_factory=_utc_now)

    @field_validator("source_reference")
    @classmethod
    def validate_source_ref(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned or cleaned.lower() in {"none", "n/a", "null", "test", "todo"}:
            raise ValueError("source_reference must cite a valid excerpt or section from the discharge plan")
        return cleaned

    @model_validator(mode="after")
    def validate_review_consistency(self) -> "TaskProposal":
        if self.status == ProposalStatus.PENDING:
            if self.reviewed_by is not None or self.reviewed_at is not None:
                raise ValueError("Pending proposals must have null reviewed_by and reviewed_at")
        else:
            if self.reviewed_by is None or self.reviewed_at is None:
                raise ValueError("Approved or Rejected proposals must specify reviewed_by and reviewed_at")
        return self


class AuditEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique audit event identifier")
    patient_id: str = Field(..., description="Reference to patient ID")
    action: AuditAction = Field(..., description="Action performed")
    entity_type: Literal["task", "proposal"] = Field(..., description="Target entity category")
    entity_id: str = Field(..., description="ID of affected entity")
    performed_by: str = Field(..., description="Actor ID or role")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured change details")
    timestamp: datetime = Field(default_factory=_utc_now)
