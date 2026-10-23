"""FastMCP Streamable HTTP Server implementation using official MCP Python SDK."""

import asyncio
from typing import Any, Dict, List, Optional
import uvicorn
from mcp.server.mcpserver import MCPServer

# Explicit FastMCP compatibility alias
FastMCP = MCPServer

from src.mcp.tools import (
    tool_approve_follow_up_task,
    tool_get_audit_log,
    tool_get_discharge_plan,
    tool_list_follow_up_tasks,
    tool_propose_follow_up_task,
)

mcp_server = MCPServer(
    name="CareSync",
    description="CareSync — Alexa+ Care Coordination Agent MCP Server",
    version="0.1.0",
)


@mcp_server.tool(
    name="get_discharge_plan",
    description="Read-only. Returns synthetic hospital discharge plan summary, source excerpts, and explicit missing fields.",
)
async def get_discharge_plan(patient_id: str) -> Dict[str, Any]:
    """Retrieve synthetic discharge plan for patient."""
    return await tool_get_discharge_plan(patient_id)


@mcp_server.tool(
    name="list_follow_up_tasks",
    description="Read-only. Returns task IDs, titles, status, owner/due-date fields, and source references.",
)
async def list_follow_up_tasks(
    patient_id: str, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List all follow-up tasks for patient, optionally filtered by status."""
    return await tool_list_follow_up_tasks(patient_id, status=status)


@mcp_server.tool(
    name="propose_follow_up_task",
    description="Creates a pending follow-up task proposal for human review. Rejects unsupported or fabricated source references. Does not create an approved task.",
)
async def propose_follow_up_task(
    patient_id: str,
    source_reference: str,
    title: str,
    due_date: Optional[str] = None,
    owner: Optional[str] = None,
) -> Dict[str, Any]:
    """Propose a new task derived from the discharge plan."""
    return await tool_propose_follow_up_task(
        patient_id=patient_id,
        source_reference=source_reference,
        title=title,
        due_date=due_date,
        owner=owner,
    )


@mcp_server.tool(
    name="approve_follow_up_task",
    description="State-changing. Explicitly approves a pending proposal, persists the task, and records audit events atomically. Repeated approval will not create duplicate tasks.",
)
async def approve_follow_up_task(
    proposal_id: str, approved_by: str
) -> Dict[str, Any]:
    """Approve a proposal and persist it as an active follow-up task."""
    return await tool_approve_follow_up_task(
        proposal_id=proposal_id, approved_by=approved_by
    )


@mcp_server.tool(
    name="get_audit_log",
    description="Read-only. Returns relevant task/proposal audit events for the patient without exposing secrets.",
)
async def get_audit_log(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieve the audit trail for a synthetic patient."""
    return await tool_get_audit_log(patient_id)


# Generate the Starlette Streamable HTTP application
from mcp.server.transport_security import TransportSecuritySettings

mcp_streamable_app = mcp_server.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def main() -> None:
    """Run standalone MCP Streamable HTTP server."""
    uvicorn.run(mcp_streamable_app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
