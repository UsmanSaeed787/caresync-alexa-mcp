# Phase 2 Specification: MCP Workflow & Streamable HTTP Protocol

> **Document Status:** Implemented & Verified  
> **Phase:** 2 of 4  
> **Source of Truth:** [AGENTS.md](file:///c:/Users/AL%20HAMD%20TRADERS/Desktop/Usman/projects/caresync-alexa-mcp/AGENTS.md)  
> **Implementation State:** Complete (38 Automated Tests Passing)

---

## 1. Objectives & Scope

Phase 2 implements the five core Model Context Protocol (MCP) tools over **Streamable HTTP** using the official Python SDK (`mcp 2.3.0`, Protocol Version `2026-07-28`), FastMCP compatibility interface, agent orchestration adapter, and comprehensive end-to-end testing of the golden-path workflow.

### 1.1 In Scope for Phase 2
- **MCP Python SDK Integration:** Installed and pinned `mcp==2.3.0` adhering to MCP specification `2026-07-28` (surpassing the required `2025-11-25+` protocol baseline).
- **Streamable HTTP Transport:** Hosted via Starlette ASGI app mounted at `/mcp` inside FastAPI and runnable standalone on port 8001.
- **Five Required MCP Tools:**
  1. `get_discharge_plan(patient_id)` — Read-only.
  2. `list_follow_up_tasks(patient_id, status?)` — Read-only.
  3. `propose_follow_up_task(patient_id, source_reference, title, due_date?, owner?)` — State-gated. Validates against discharge plan.
  4. `approve_follow_up_task(proposal_id, approved_by)` — State-changing. Idempotent approval, atomic task creation and audit logging.
  5. `get_audit_log(patient_id)` — Read-only.
- **Source Reference Validation:** `validate_source_reference` verifying genuine text excerpts from `seed_data.json` / patient plan.
- **Deterministic Agent Adapter:** `DeterministicAgentAdapter` driving the golden-path demo offline without paid LLM API requirements.
- **API Endpoints:**
  - `POST /api/v1/agent/chat`
  - `GET /api/v1/tasks`
  - `POST /api/v1/tasks/propose`
  - `POST /api/v1/tasks/approve`
  - `GET /api/v1/audit`
- **Testing:** 38 unit and integration tests covering domain models, foreign keys, rollback, source reference validation, seeder idempotency, MCP tools, Streamable HTTP handshake, and agent adapter turns.

### 1.2 Out of Scope for Phase 2 (Deferred to Phase 3 & 4)
- **Phase 3:** Next.js + Tailwind CSS simulator UI, Patient context panel, follow-up board, approval modal, and audit log table.
- **Phase 4:** Production hardening, sub-three-minute video demo, Devpost submission packaging.

---

## 2. Tool Contracts & Schemas

### 2.1 `get_discharge_plan`
- **Parameters:** `patient_id: str`
- **Output:**
  ```json
  {
    "patient_id": "patient-synthetic-001",
    "admission_date": "2026-10-14",
    "discharge_date": "2026-10-20",
    "summary": "Synthetic post-discharge coordination plan...",
    "source_text": "DISCHARGE SUMMARY (SYNTHETIC RECORD)...",
    "source_excerpts": [
      {
        "category": "PCP Follow-Up",
        "text": "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
      }
    ],
    "explicit_missing_fields": ["cardiology_follow_up_date", "lab_coordinator_owner"],
    "is_synthetic": true
  }
  ```

### 2.2 `list_follow_up_tasks`
- **Parameters:** `patient_id: str`, `status: Optional[str] = None`
- **Output:** List of task items with `due_date` and `owner` preserved as explicit `null` when unassigned.

### 2.3 `propose_follow_up_task`
- **Parameters:** `patient_id: str`, `source_reference: str`, `title: str`, `due_date: Optional[str] = None`, `owner: Optional[str] = None`
- **Validation:** `source_reference` is checked against `plan.source_text` and `plan.source_excerpts`. Unsupported text raises `ValueError`.
- **Output:** Created proposal object with `status: "PENDING"`.

### 2.4 `approve_follow_up_task`
- **Parameters:** `proposal_id: str`, `approved_by: str`
- **Idempotency:** Re-approving an already approved proposal returns the previously created task without duplicate rows or duplicate events.
- **Output:** Object with `status: "APPROVED"` and `task: FollowUpTask`.

### 2.5 `get_audit_log`
- **Parameters:** `patient_id: str`
- **Output:** List of timestamped `AuditEvent` entries.

---

## 3. Streamable HTTP Protocol Details

- **SDK:** `mcp 2.3.0`
- **Protocol Version:** `2026-07-28`
- **Mounted Path:** `/mcp` on `http://127.0.0.1:8000`
- **Standalone Server Command:** `py -m src.mcp.server` (port 8001)
- **Security:** `enable_dns_rebinding_protection=False` for local development.

---

## 4. Test Verification Summary

- Total Tests: **38 passed in 2.71s**
- Test Breakdown:
  - `test_agent_adapter.py`: 5 tests
  - `test_api.py`: 4 tests
  - `test_database.py`: 6 tests
  - `test_domain_models.py`: 9 tests
  - `test_mcp_streamable_http.py`: 3 tests
  - `test_mcp_tools.py`: 9 tests
  - `test_seeder.py`: 2 tests
