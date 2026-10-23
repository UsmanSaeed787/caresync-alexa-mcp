"""API tests for /health and /api/v1/context endpoints."""

from httpx import AsyncClient
import pytest

from src.data.seeder import seed_synthetic_data


async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Verify health check endpoint returns 200 and healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "CareSync API"
    assert data["synthetic_data_mode"] is True
    assert data["database"] == "connected"
    assert data["version"] == "0.1.0"


async def test_context_endpoint(async_client: AsyncClient, test_db_path: str) -> None:
    """Verify patient context returns synthetic data and safety disclaimer."""
    await seed_synthetic_data(db_path_override=test_db_path)

    # 1. Valid patient
    response = await async_client.get("/api/v1/context?patient_id=patient-synthetic-001")
    assert response.status_code == 200
    data = response.json()
    assert data["patient"]["id"] == "patient-synthetic-001"
    assert data["patient"]["mrn"] == "SYNTH-MRN-84920"
    assert data["patient"]["is_synthetic"] is True
    assert data["discharge_plan"]["id"] == "plan-synthetic-001"
    assert "SYNTHETIC DEMO DATA ONLY" in data["safety_disclaimer"]

    # 2. Unknown synthetic patient -> 404
    response_404 = await async_client.get("/api/v1/context?patient_id=patient-synthetic-999")
    assert response_404.status_code == 404
    detail = response_404.json().get("detail", "")
    assert "not found" in detail.lower()

    # 3. Non-synthetic query -> 400
    response_400 = await async_client.get("/api/v1/context?patient_id=real-ehr-patient-001")
    assert response_400.status_code == 400
    detail_400 = response_400.json().get("detail", "")
    assert "synthetic" in detail_400.lower()


async def test_agent_chat_api(async_client: AsyncClient, test_db_path: str) -> None:
    """Verify POST /api/v1/agent/chat returns tool calls and structured response."""
    await seed_synthetic_data(db_path_override=test_db_path)

    # 1. Inquire outstanding follow-ups
    chat_res = await async_client.post(
        "/api/v1/agent/chat",
        json={"prompt": "What follow-ups are still outstanding?", "patient_id": "patient-synthetic-001"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert "Eleanor Vance" in data["response_text"]
    assert len(data["tool_calls"]) == 2

    # 2. Prepare proposal
    prop_res = await async_client.post(
        "/api/v1/agent/chat",
        json={"prompt": "Prepare a follow-up task for the primary-care appointment", "patient_id": "patient-synthetic-001"},
    )
    assert prop_res.status_code == 200
    prop_data = prop_res.json()
    assert prop_data["pending_proposal"] is not None
    proposal_id = prop_data["pending_proposal"]["proposal_id"]

    # 3. Approve via chat
    appr_res = await async_client.post(
        "/api/v1/agent/chat",
        json={"prompt": f"Approve proposal {proposal_id}", "patient_id": "patient-synthetic-001"},
    )
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert "approved" in appr_data["response_text"].lower()


async def test_tasks_and_audit_rest_endpoints(async_client: AsyncClient, test_db_path: str) -> None:
    """Verify REST endpoints for listing tasks, proposing, approving, and viewing audit trail."""
    await seed_synthetic_data(db_path_override=test_db_path)

    # 1. List tasks
    list_res = await async_client.get("/api/v1/tasks?patient_id=patient-synthetic-001")
    assert list_res.status_code == 200
    tasks = list_res.json()
    assert len(tasks) == 3

    # 2. Propose task
    excerpt = "Order basic metabolic panel (BMP) in 10-14 days to monitor renal function after furosemide adjustment."
    prop_res = await async_client.post(
        "/api/v1/tasks/propose",
        json={
            "patient_id": "patient-synthetic-001",
            "title": "BMP Blood Work",
            "source_reference": excerpt,
            "due_date": None,
            "owner": None,
        },
    )
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["proposal_id"]

    # 3. Approve task
    appr_res = await async_client.post(
        "/api/v1/tasks/approve",
        json={"proposal_id": proposal_id, "approved_by": "Coordinator Alex"},
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 4. View audit trail
    audit_res = await async_client.get("/api/v1/audit?patient_id=patient-synthetic-001")
    assert audit_res.status_code == 200
    audit = audit_res.json()
    actions = [ev["action"] for ev in audit]
    assert "PROPOSAL_CREATED" in actions
    assert "PROPOSAL_APPROVED" in actions
    assert "TASK_CREATED" in actions


async def test_proposals_and_rejection_rest_endpoints(async_client: AsyncClient, test_db_path: str) -> None:
    """Verify listing proposals and rejecting a proposal via REST."""
    await seed_synthetic_data(db_path_override=test_db_path)

    # 1. Propose task
    excerpt = "Order basic metabolic panel (BMP) in 10-14 days to monitor renal function after furosemide adjustment."
    prop_res = await async_client.post(
        "/api/v1/tasks/propose",
        json={
            "patient_id": "patient-synthetic-001",
            "title": "BMP Blood Work To Reject",
            "source_reference": excerpt,
            "due_date": None,
            "owner": None,
        },
    )
    assert prop_res.status_code == 200
    proposal_id = prop_res.json()["proposal_id"]

    # 2. List proposals
    list_res = await async_client.get("/api/v1/proposals?patient_id=patient-synthetic-001&status=PENDING")
    assert list_res.status_code == 200
    props = list_res.json()
    assert any(p["id"] == proposal_id for p in props)

    # 3. Reject proposal
    rej_res = await async_client.post(
        "/api/v1/tasks/reject",
        json={"proposal_id": proposal_id, "rejected_by": "Coordinator Alex", "reason": "Redundant task"},
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "REJECTED"

    # 4. Verify audit trail logs rejection
    audit_res = await async_client.get("/api/v1/audit?patient_id=patient-synthetic-001")
    assert audit_res.status_code == 200
    audit = audit_res.json()
    assert any(ev["action"] == "PROPOSAL_REJECTED" and ev["entity_id"] == proposal_id for ev in audit)

