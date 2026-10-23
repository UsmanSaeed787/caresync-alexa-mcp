"""Tests verifying MCP Streamable HTTP server endpoints and tool invocation."""

import json
import pytest
from starlette.testclient import TestClient

from src.data.seeder import seed_synthetic_data
from src.main import app
from src.mcp.server import mcp_server


@pytest.fixture(autouse=True)
async def seed_data(test_db_path: str) -> None:
    await seed_synthetic_data(db_path_override=test_db_path)


def test_mcp_streamable_http_initialization() -> None:
    """Verify MCP Streamable HTTP server handles initialize handshake over HTTP."""
    with TestClient(app) as client:
        # Check /health reports mcp_endpoint
        health_res = client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["mcp_endpoint"] == "/mcp"

        # Send Streamable HTTP JSON-RPC initialize handshake to mounted endpoint
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2026-07-28",
                "capabilities": {},
                "clientInfo": {"name": "alexa-care-simulator", "version": "1.0"},
            },
        }

        response = client.post("/mcp/", json=init_payload)
        assert response.status_code == 200
        # Streamable HTTP returns SSE event or json response
        text = response.text
        assert "jsonrpc" in text
        assert "2026-07-28" in text or "capabilities" in text


async def test_mcp_server_lists_all_five_tools() -> None:
    """Verify MCP server registers the 5 required tools per AGENTS.md."""
    tools = await mcp_server.list_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "get_discharge_plan",
        "list_follow_up_tasks",
        "propose_follow_up_task",
        "approve_follow_up_task",
        "get_audit_log",
    ]

    for expected in expected_tools:
        assert expected in tool_names, f"Tool '{expected}' must be registered on MCP server"


async def test_mcp_server_call_tools_end_to_end() -> None:
    """Verify direct MCP tool calls execute the complete golden path."""
    patient_id = "patient-synthetic-001"

    # 1. get_discharge_plan
    plan_res = await mcp_server.call_tool("get_discharge_plan", {"patient_id": patient_id})
    assert not plan_res.is_error
    assert len(plan_res.content) > 0

    # 2. list_follow_up_tasks
    tasks_res = await mcp_server.call_tool("list_follow_up_tasks", {"patient_id": patient_id})
    assert not tasks_res.is_error

    # 3. propose_follow_up_task
    excerpt = "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
    title = "Primary Care Exam"
    prop_res = await mcp_server.call_tool(
        "propose_follow_up_task",
        {
            "patient_id": patient_id,
            "source_reference": excerpt,
            "title": title,
            "due_date": "2026-10-27",
            "owner": None,
        },
    )
    assert not prop_res.is_error
    prop_data = json.loads(prop_res.content[0].text) if hasattr(prop_res.content[0], "text") else prop_res.content[0]
    proposal_id = prop_data["proposal_id"]

    # 4. approve_follow_up_task
    appr_res = await mcp_server.call_tool(
        "approve_follow_up_task",
        {"proposal_id": proposal_id, "approved_by": "Coordinator Maria"},
    )
    assert not appr_res.is_error
    appr_data = json.loads(appr_res.content[0].text) if hasattr(appr_res.content[0], "text") else appr_res.content[0]
    assert appr_data["status"] == "APPROVED"

    # 5. get_audit_log
    audit_res = await mcp_server.call_tool("get_audit_log", {"patient_id": patient_id})
    assert not audit_res.is_error
