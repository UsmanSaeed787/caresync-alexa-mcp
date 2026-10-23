"""FastAPI application entrypoint for CareSync API with mounted MCP Streamable HTTP server."""

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.agent.adapter import AgentTurnResult, get_agent_adapter
from src.config import settings
from src.data.seeder import seed_synthetic_data
from src.db.connection import get_db, init_db
from src.db.repository import CareSyncRepository
from src.domain.enums import ProposalStatus
from src.mcp.server import mcp_streamable_app
from src.mcp.tools import (
    tool_approve_follow_up_task,
    tool_get_audit_log,
    tool_list_follow_up_tasks,
    tool_propose_follow_up_task,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database tables, run idempotent seeder, and manage MCP Streamable HTTP session manager."""
    await init_db()
    if settings.SEED_ON_STARTUP:
        await seed_synthetic_data()
    async with mcp_streamable_app.router.lifespan_context(mcp_streamable_app):
        yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="CareSync — Alexa+ Care Coordination Agent Backend (Synthetic MVP)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the MCP Streamable HTTP Starlette app
app.mount("/mcp", mcp_streamable_app)


class HealthResponse(BaseModel):
    status: str
    service: str
    synthetic_data_mode: bool
    database: str
    version: str
    mcp_endpoint: str


class PatientContextResponse(BaseModel):
    patient: Dict[str, Any]
    discharge_plan: Optional[Dict[str, Any]]
    safety_disclaimer: str


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Coordinator prompt or instruction")
    patient_id: str = Field(default="patient-synthetic-001", description="Synthetic patient identifier")


class ProposeTaskRequest(BaseModel):
    patient_id: str
    title: str
    source_reference: str
    due_date: Optional[str] = None
    owner: Optional[str] = None


class ApproveTaskRequest(BaseModel):
    proposal_id: str
    approved_by: str = "Care Coordinator Alex"


class RejectTaskRequest(BaseModel):
    proposal_id: str
    rejected_by: str = "Care Coordinator Alex"
    reason: str = "Rejected in simulator"


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Service liveness and database connectivity verification."""
    db_status = "disconnected"
    try:
        async with get_db() as db:
            async with db.execute("SELECT 1;") as cursor:
                row = await cursor.fetchone()
                if row and row[0] == 1:
                    db_status = "connected"
    except Exception as exc:
        db_status = f"error: {str(exc)}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        service=settings.APP_NAME,
        synthetic_data_mode=settings.SYNTHETIC_DATA_MODE,
        database=db_status,
        version=settings.APP_VERSION,
        mcp_endpoint="/mcp",
    )


@app.get("/api/v1/context", response_model=PatientContextResponse)
async def get_patient_context(
    patient_id: str = Query(default="patient-synthetic-001", description="Synthetic patient ID")
) -> PatientContextResponse:
    """Retrieve synthetic patient profile and discharge plan for the context panel."""
    if not patient_id.startswith("patient-synthetic") and "synth" not in patient_id.lower():
        raise HTTPException(
            status_code=400,
            detail="Only synthetic patient IDs are accepted by this prototype (must contain 'synth').",
        )
    async with get_db() as db:
        repo = CareSyncRepository(db)
        patient = await repo.get_patient(patient_id)
        if not patient:
            raise HTTPException(
                status_code=404,
                detail=f"Synthetic patient '{patient_id}' not found."
            )
        plan = await repo.get_discharge_plan_by_patient_id(patient_id)

    return PatientContextResponse(
        patient=patient.model_dump(mode="json"),
        discharge_plan=plan.model_dump(mode="json") if plan else None,
        safety_disclaimer="SYNTHETIC DEMO DATA ONLY. Not for clinical decision-making, diagnosis, or real patient care.",
    )


@app.post("/api/v1/agent/chat", response_model=AgentTurnResult)
async def agent_chat(request: ChatRequest) -> AgentTurnResult:
    """Process a user conversational turn via the CareSync Agent adapter with MCP tool calling."""
    if not request.patient_id.startswith("patient-synthetic") and "synth" not in request.patient_id.lower():
        raise HTTPException(
            status_code=400,
            detail="Only synthetic patient IDs are accepted by this prototype.",
        )
    adapter = get_agent_adapter()
    return await adapter.process_user_turn(
        prompt=request.prompt, patient_id=request.patient_id
    )


@app.get("/api/v1/tasks", response_model=List[Dict[str, Any]])
async def list_tasks(
    patient_id: str = Query(default="patient-synthetic-001"),
    status: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List active follow-up tasks."""
    try:
        return await tool_list_follow_up_tasks(patient_id=patient_id, status=status)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/tasks/propose", response_model=Dict[str, Any])
async def propose_task(request: ProposeTaskRequest) -> Dict[str, Any]:
    """Create a pending follow-up proposal."""
    try:
        return await tool_propose_follow_up_task(
            patient_id=request.patient_id,
            source_reference=request.source_reference,
            title=request.title,
            due_date=request.due_date,
            owner=request.owner,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/tasks/approve", response_model=Dict[str, Any])
async def approve_task(request: ApproveTaskRequest) -> Dict[str, Any]:
    """Approve a pending proposal and persist it to active follow-up workflow."""
    try:
        return await tool_approve_follow_up_task(
            proposal_id=request.proposal_id, approved_by=request.approved_by
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/proposals", response_model=List[Dict[str, Any]])
async def list_proposals(
    patient_id: str = Query(default="patient-synthetic-001"),
    status: Optional[str] = Query(default=None),
) -> List[Dict[str, Any]]:
    """List task proposals (pending, approved, rejected)."""
    if not patient_id.startswith("patient-synthetic") and "synth" not in patient_id.lower():
        raise HTTPException(
            status_code=400,
            detail="Only synthetic patient IDs are accepted by this prototype.",
        )
    async with get_db() as db:
        repo = CareSyncRepository(db)
        prop_status = ProposalStatus(status) if status else None
        proposals = await repo.list_proposals(patient_id=patient_id, status=prop_status)
        return [p.model_dump(mode="json") for p in proposals]


@app.post("/api/v1/tasks/reject", response_model=Dict[str, Any])
async def reject_task(request: RejectTaskRequest) -> Dict[str, Any]:
    """Reject a pending proposal and log audit event."""
    async with get_db() as db:
        repo = CareSyncRepository(db)
        try:
            proposal = await repo.reject_proposal(
                proposal_id=request.proposal_id,
                rejected_by=request.rejected_by,
                reason=request.reason,
            )
            return proposal.model_dump(mode="json")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/audit", response_model=List[Dict[str, Any]])
async def get_audit_trail(
    patient_id: str = Query(default="patient-synthetic-001"),
) -> List[Dict[str, Any]]:
    """Retrieve audit history trail."""
    try:
        return await tool_get_audit_log(patient_id=patient_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
