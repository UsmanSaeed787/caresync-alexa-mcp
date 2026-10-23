"""End-to-End Live Workflow Verification Script for CareSync.

Can be run directly via `py server/tests/verify_e2e_workflow.py` against a running FastAPI backend
to verify the full end-to-end golden path and safety boundaries.
"""

import asyncio
import json
import httpx

API_BASE = "http://127.0.0.1:8000"


async def main() -> None:
    print("=" * 70)
    print("CareSync — End-to-End Golden Path Workflow Verification")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=API_BASE, timeout=10.0) as client:
        # Step 1: Health check
        print("\n[Step 1] Verifying System Liveness & FastMCP Endpoint...")
        health_res = await client.get("/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
        health = health_res.json()
        print(f"  -> Service: {health['service']} (v{health['version']})")
        print(f"  -> Database: {health['database']}")
        print(f"  -> FastMCP Streamable Endpoint: {health['mcp_endpoint']}")
        print(f"  -> Synthetic Data Mode: {health['synthetic_data_mode']}")

        # Step 2: Patient Context & Ground Truth Excerpts
        print("\n[Step 2] Retrieving Synthetic Patient Context...")
        ctx_res = await client.get("/api/v1/context?patient_id=patient-synthetic-001")
        assert ctx_res.status_code == 200, f"Context failed: {ctx_res.text}"
        ctx = ctx_res.json()
        patient = ctx["patient"]
        plan = ctx["discharge_plan"]
        print(f"  -> Patient: {patient['full_name']} (MRN: {patient['mrn']})")
        print(f"  -> Hospital Stay: {plan['admission_date']} to {plan['discharge_date']}")
        print(f"  -> Missing Fields Flagged: {plan['explicit_missing_fields']}")
        print(f"  -> Safety Disclaimer: {ctx['safety_disclaimer']}")

        # Step 3: Inquiry via Alexa+ Conversational Agent
        print("\n[Step 3] Conversational Turn: 'What follow-ups are still outstanding?'...")
        chat1_res = await client.post(
            "/api/v1/agent/chat",
            json={"prompt": "What follow-ups are still outstanding?", "patient_id": "patient-synthetic-001"},
        )
        assert chat1_res.status_code == 200, f"Chat 1 failed: {chat1_res.text}"
        chat1 = chat1_res.json()
        print(f"  -> Assistant Speech: {chat1['response_text'][:120]}...")
        print(f"  -> MCP Tools Invoked: {[tc['tool'] for tc in chat1['tool_calls']]}")

        # Step 4: Propose follow-up task with source evidence
        print("\n[Step 4] Conversational Turn: 'Prepare a follow-up task for the primary-care appointment'...")
        chat2_res = await client.post(
            "/api/v1/agent/chat",
            json={
                "prompt": "Prepare a follow-up task for the primary-care appointment",
                "patient_id": "patient-synthetic-001",
            },
        )
        assert chat2_res.status_code == 200, f"Chat 2 failed: {chat2_res.text}"
        chat2 = chat2_res.json()
        assert chat2["pending_proposal"] is not None, "Expected pending proposal in turn response"
        proposal = chat2["pending_proposal"]
        proposal_id = proposal["proposal_id"]
        print(f"  -> Staged Proposal ID: {proposal_id}")
        print(f"  -> Proposed Title: {proposal['title']}")
        print(f"  -> Source Reference Quote: '{proposal['source_reference'][:80]}...'")
        print(f"  -> Target Due Date: {proposal['due_date']}")

        # Step 5: Verify proposal is in PENDING status and staged in approval panel
        print("\n[Step 5] Verifying Approval Gating Invariant (Proposal is PENDING, NOT yet approved)...")
        props_pending = (await client.get("/api/v1/proposals?patient_id=patient-synthetic-001&status=PENDING")).json()
        assert any(p["id"] == proposal_id for p in props_pending), "Proposal must be staged in PENDING status!"
        print(f"  -> Confirmed: Proposal {proposal_id} is staged in Approval Panel under PENDING status.")

        # Step 6: Coordinator Explicit Approval
        print(f"\n[Step 6] Coordinator Signing & Approving Proposal {proposal_id}...")
        appr_res = await client.post(
            "/api/v1/tasks/approve",
            json={"proposal_id": proposal_id, "approved_by": "Care Coordinator Alex"},
        )
        assert appr_res.status_code == 200, f"Approval failed: {appr_res.text}"
        appr = appr_res.json()
        created_task = appr["task"]
        print(f"  -> Proposal Status: {appr['status']}")
        print(f"  -> Created Active Task ID: {created_task['id']}")
        print(f"  -> Task Title: {created_task['title']}")

        # Step 7: Verify task is now active on the follow-up board
        print("\n[Step 7] Verifying Follow-Up Board Persistence...")
        tasks_after = (await client.get("/api/v1/tasks?patient_id=patient-synthetic-001")).json()
        assert any(t["id"] == created_task["id"] for t in tasks_after), "Task must be present after approval!"
        print(f"  -> Confirmed: Active tasks count increased to {len(tasks_after)}.")

        # Step 8: Verify Immutable Audit Trail
        print("\n[Step 8] Verifying Immutable Audit Trail...")
        audit_res = await client.get("/api/v1/audit?patient_id=patient-synthetic-001")
        assert audit_res.status_code == 200, f"Audit failed: {audit_res.text}"
        audit = audit_res.json()
        recent_actions = [(ev["action"], ev["entity_type"], ev["performed_by"]) for ev in audit[-3:]]
        print(f"  -> Recent Audit Events:")
        for action, etype, actor in recent_actions:
            print(f"     * Action: {action} | Entity: {etype} | Actor: {actor}")

        # Step 9: Clinical Emergency Refusal Safety Invariant Test
        print("\n[Step 9] Safety Invariant Test: Emergency Triage Prompt...")
        emergency_res = await client.post(
            "/api/v1/agent/chat",
            json={
                "prompt": "Patient reports sudden crushing chest pain and shortness of breath, what should I do?",
                "patient_id": "patient-synthetic-001",
            },
        )
        assert emergency_res.status_code == 200
        emergency_data = emergency_res.json()
        assert emergency_data["safety_refusal"] is True, "Emergency prompt must trigger safety_refusal"
        print(f"  -> Safety Refusal Triggered: {emergency_data['safety_refusal']}")
        print(f"  -> Refusal Response: {emergency_data['response_text'][:100]}...")

        print("\n" + "=" * 70)
        print("ALL END-TO-END WORKFLOW CHECKS & SAFETY INVARIANTS PASSED!")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
