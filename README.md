# CareSync — Alexa+ Care Coordination Agent

> **Amazon Developer Hackathon — Primary Track:** Amazon Alexa+  
> **Status:** Hackathon MVP (Tested Prototype)  
> **Repository Single Source of Truth:** [`AGENTS.md`](./AGENTS.md)  
> **Protocol:** Real Model Context Protocol (MCP) Server over **Streamable HTTP** (MCP Specification `2026-07-28` / `2025-11-25+`)

[![M8ven Score](https://m8ven.ai/badge/mcp/usmansaeed787-caresync-alexa-mcp-020ync?v=623e4e79a6c16e81ea4a478300a9f4fa)](https://m8ven.ai/mcp/usmansaeed787-caresync-alexa-mcp-020ync?s=readme)

---

## ⚠️ Prototype Safety & Synthetic Data Notice

**STRICTLY SYNTHETIC DATA ONLY — NOT FOR CLINICAL USE.**

CareSync is an administrative care coordination simulation built for the Amazon Developer Hackathon.
- **Non-Goals:** CareSync **MUST NOT** diagnose, triage symptoms, recommend treatments, calculate clinical risk, prescribe/discontinue medications, or contact real patients, emergency services, or external healthcare systems.
- **Synthetic Data Boundary:** All patient records (`Eleanor Vance [SYNTHETIC]`), identifiers (`SYNTH-MRN-84920`), and clinical scenarios are entirely fictional and bundled locally.
- **Honest Simulation Disclaimer:** The web workspace is an **Alexa+-style simulation** communicating over live Streamable HTTP MCP tools. It is not connected to physical Alexa+ hardware or private production EHR accounts.
- **Emergency Invariant:** If an emergency or symptom inquiry is presented, CareSync strictly refuses clinical triage and directs the user to local emergency services or a qualified healthcare professional as appropriate.

---

## 1. Executive Summary & Product Outcome

Hospital discharge plans are dense, multi-page narratives often missing critical ownership and exact dates. Patients and care coordinators are left asking:
- *What follow-up tasks are required by this discharge plan?*
- *Which tasks are still pending, completed, or missing an assigned owner?*
- *Can a voice assistant prepare a reminder or follow-up task safely without hallucinating missing details?*
- *Who approved the task, what verbatim discharge text supports it, and when was it logged?*

**The CareSync Outcome:** A voice-first assistant that turns complex synthetic hospital discharge instructions into an **approval-gated, auditable follow-up checklist with source evidence**—not an ungrounded chatbot that merely summarizes medical text.

---

## 2. Architecture & Technology Stack

CareSync utilizes a small, hardened, test-driven architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CareSync Simulator UI (Next.js 14)                     │
│    Header Banner  •  Patient Context Panel  •  Follow-Up Board (Checklist)  │
│       Approval Panel (Human Gate)  •  Conversation Panel (Alexa+ Voice)     │
│                         Immutable Audit Trail                               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Live REST & JSON RPC Calls
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Backend (Port 8000)                       │
│    /health  •  /api/v1/context  •  /api/v1/tasks  •  /api/v1/agent/chat     │
│                 /api/v1/tasks/approve  •  /api/v1/audit                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Mounted Sub-App Lifespan
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             Streamable HTTP FastMCP Server (/mcp) — Spec 2026-07-28         │
│  [1] get_discharge_plan       [2] list_follow_up_tasks                      │
│  [3] propose_follow_up_task   [4] approve_follow_up_task                    │
│  [5] get_audit_log                                                          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Strict Domain Validation
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   Domain Layer & Repository (CareSyncRepository)            │
│    • Verbatim Source Reference Validator (Rejects Fabricated Excerpts)      │
│    • Polymorphic Referential Integrity (Tasks & Proposals Isolated)         │
│    • Compare-And-Swap (CAS) Atomic Approvals (BEGIN IMMEDIATE Concurrency)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ aiosqlite (Foreign Keys Enabled)
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             SQLite Database                                 │
│        patients  •  discharge_plans  •  follow_up_tasks  •  audit_events     │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind CSS (`simulator/`).
- **Backend API:** Python 3.11+ / 3.13 + FastAPI + Starlette (`server/`).
- **MCP Server:** Official MCP Python SDK (`mcp==2.3.0`, FastMCP, Streamable HTTP protocol).
- **Agent Adapter:** Extensible Agent Adapter with `DeterministicAgentAdapter` driving the offline golden path with real MCP tool invocations.
- **Database:** Local SQLite (`caresync_local.db`) with explicit foreign key constraints, transaction boundaries, and compare-and-swap concurrency guards.

---

## 3. Real Streamable HTTP MCP Tool Contract

CareSync exposes **five dedicated tools** over Streamable HTTP (`/mcp`):

| Tool Name | Type | Description |
| :--- | :--- | :--- |
| `get_discharge_plan(patient_id)` | Read-Only | Retrieves synthetic plan summary, admission/discharge dates, verbatim excerpts, and explicitly missing fields. |
| `list_follow_up_tasks(patient_id, status?)` | Read-Only | Returns active follow-up checklist, owners, due dates, source references, and human review flags. |
| `propose_follow_up_task(patient_id, source_reference, title, due_date?, owner?)` | Approval-Gated | Validates `source_reference` against verbatim plan text. Staged in the **Approval Panel** under `PENDING`. Rejects fabricated evidence. Does **not** insert active task. |
| `approve_follow_up_task(proposal_id, approved_by)` | State-Changing | Explicit human coordinator signature. Atomically transitions proposal to `APPROVED`, persists the active task, triggers simulated reminders, and appends `TASK_CREATED` and `PROPOSAL_APPROVED` audit events. Idempotent retry-safe. |
| `get_audit_log(patient_id)` | Read-Only | Returns immutable append-only provenance trail of coordinator actions, timestamps, and entity metadata. |

---

## 4. Getting Started (Step-by-Step Setup)

### 4.1 Prerequisites
- **Python:** 3.11 or later (verified on Python 3.13 on Windows).
- **Node.js:** v18 or later (with `npm`).
- **Operating System:** Windows PowerShell, macOS, or Linux.

### 4.2 Installation & Environment Setup

#### 1. Clone & Configure Environment
```powershell
# From repository root:
Copy-Item .env.example .env
Copy-Item server/.env.example server/.env
Copy-Item simulator/.env.example simulator/.env.local
```

#### 2. Backend & MCP Server Setup
```powershell
# Create and activate Python virtual environment
py -m venv server/.venv
.\server\.venv\Scripts\Activate.ps1

# Install pinned dependencies
python -m pip install --upgrade pip
python -m pip install -r server/requirements.txt

# Run automated test suite (50 unit, integration, and hardening tests)
python -m pytest server/tests -v
```

#### 3. Frontend Simulator Setup
```powershell
# From repository root, navigate to simulator
cd simulator

# Install Node dependencies
npm.cmd install

# Build production bundle
npm.cmd run build
```

### 4.3 Running CareSync Locally

Open two separate terminals from the repository root:

**Terminal 1 — Backend & FastMCP Streamable Server:**
```powershell
.\server\.venv\Scripts\python.exe -m uvicorn src.main:app --app-dir server --port 8000 --host 127.0.0.1
```
*Output will confirm:*
`StreamableHTTP session manager started`  
`Uvicorn running on http://127.0.0.1:8000`

**Terminal 2 — Next.js Simulator UI:**
```powershell
cd simulator
npm.cmd run start
```
*Access the workspace in your browser at:* **`http://localhost:3000`**

---

## 5. Sub-3-Minute Video Demo Script

Follow this exact golden path walkthrough for the video presentation:

| Time | Screen / Panel | Spoken Script / Action | Outcome Demonstrated |
| :--- | :--- | :--- | :--- |
| **0:00 - 0:35** | **Header & Patient Context Panel** | *"Welcome to CareSync, our Alexa+ Care Coordination Agent for the Amazon Developer Hackathon. We are looking at a synthetic hospital discharge for Eleanor Vance, who was admitted for congestive heart failure. Note our prominent safety label: this is synthetic data and strictly non-clinical. Notice also the live system status indicator showing that our backend and Streamable HTTP FastMCP server are connected."* | Proves synthetic boundaries, system health, and honest Alexa+ simulation labeling. |
| **0:35 - 1:10** | **Follow-Up Board & Missing Fields** | *"In the Follow-Up Board, we see initial post-discharge tasks. Notice how missing information is treated with honesty: unstated due dates and unassigned owners are explicitly rendered as 'Unset' and 'Unassigned', and flagged for human review—never hallucinated."* | Demonstrates truthfulness invariant and explicit null handling. |
| **1:10 - 1:50** | **Conversation Panel & MCP Tool Calling** | *Click the quick prompt: 'What follow-ups are still outstanding?'.*<br>*"Our Alexa+ voice assistant invokes the live MCP tools `get_discharge_plan` and `list_follow_up_tasks`. We can click to inspect the real-time MCP arguments and server payloads returned over Streamable HTTP."* | Verifies real MCP tool calling over Streamable HTTP—zero fake frontend data. |
| **1:50 - 2:25** | **Approval Gating & Task Persistence** | *Click: 'Prepare a follow-up task for the primary-care appointment'.*<br>*"The agent calls `propose_follow_up_task`, citing the verbatim discharge text. Notice our human approval gate: the proposal is staged in the Approval Panel under 'Pending Human Approval'. It is NOT on the active board yet. When the coordinator clicks 'Approve & Schedule Task', the proposal is confirmed, the task appears on the board, and a simulated reminder is activated."* | Demonstrates explicit human-in-the-loop approval gating and source evidence. |
| **2:25 - 2:45** | **Immutable Audit Trail** | *Scroll to Audit Trail.*<br>*"Every action is recorded in an immutable, append-only audit trail showing the actor, timestamp, and entity payload. Re-approving or duplicate requests are safely deduplicated."* | Proves audit integrity and idempotency. |
| **2:45 - 3:00** | **Safety Emergency Test** | *Click: 'Emergency Safety Test' ('Crushing chest pain...').*<br>*"Finally, when presented with a medical emergency, CareSync strictly refuses clinical triage and displays immediate emergency guidance directing the user to local emergency services or a qualified healthcare professional."* | Proves clinical safety guardrails. |

---

## 6. Real Friction Log & Developer Feedback

In accordance with hackathon instructions, here is an honest friction log of issues encountered and architectural solutions:

1. **FastMCP Streamable HTTP Lifespan in FastAPI (`Task group is not initialized`):**
   - *Friction:* Sub-mounting FastMCP's Streamable HTTP Starlette app (`mcp_streamable_app`) inside FastAPI caused `RuntimeError: Task group is not initialized` on incoming client connections because Starlette's `lifespan` handler was not entered automatically by FastAPI's parent lifespan.
   - *Resolution:* Wrapped the FastAPI parent lifespan with `async with mcp_streamable_app.router.lifespan_context(mcp_streamable_app): yield`. This cleanly initializes the `StreamableHttpManager` worker task groups.
2. **Local Host Header Security (`DNS Rebinding Protection`):**
   - *Friction:* FastMCP 2.x enforces strict DNS rebinding protections by default, rejecting local requests forwarded by proxies or test clients without explicitly configured allowed hosts.
   - *Resolution:* Configured `TransportSecuritySettings(enable_dns_rebinding_protection=False)` for local development in `server/src/mcp/server.py`.
3. **Database Concurrency in SQLite (`database is locked` / Double Approvals):**
   - *Friction:* Concurrent approval attempts from multiple browser tabs or API retries risked creating duplicate follow-up tasks if two transactions read the proposal simultaneously before updating.
   - *Resolution:* Implemented `BEGIN IMMEDIATE;` transaction locking and atomic Compare-And-Swap (CAS): `UPDATE task_proposals SET status = 'APPROVED' WHERE id = ? AND status = 'PENDING'`. If `cur.rowcount == 0`, the transaction safely looks up the winning task and returns it without inserting duplicates.
4. **Dependency Conflicts with MCP SDK and Starlette:**
   - *Friction:* The modern `mcp` SDK (v2.3.0) requires `starlette>=0.40.0,<1.0.0` and `sse-starlette>=3.0.0`, which conflicted with older FastAPI pins.
   - *Resolution:* Pinned `fastapi==0.161.1`, `starlette==1.9.0`, and `sse-starlette==3.5.0` in `requirements.txt`, passing `pip check` with 0 broken dependencies.

---

## 7. Automated Test Suite (50 Passing Tests)

CareSync includes 50 automated tests covering unit, database integrity, MCP tool contracts, Streamable HTTP protocol, and hardening:

```powershell
.\server\.venv\Scripts\python.exe -m pytest server\tests -v
```

```
server/tests/test_agent_adapter.py (5 tests)
  ✓ test_agent_inquire_outstanding_tasks
  ✓ test_agent_prepare_follow_up_task
  ✓ test_agent_approve_follow_up_task
  ✓ test_agent_audit_log_inquiry
  ✓ test_agent_clinical_triage_refusal

server/tests/test_api.py (5 tests)
  ✓ test_health_endpoint
  ✓ test_context_endpoint
  ✓ test_agent_chat_api
  ✓ test_tasks_and_audit_rest_endpoints
  ✓ test_proposals_and_rejection_rest_endpoints

server/tests/test_database.py (6 tests)
  ✓ test_foreign_key_enforcement
  ✓ test_proposal_review_consistency
  ✓ test_patient_mrn_uniqueness
  ✓ test_transaction_rollback
  ✓ test_multistep_transaction_rollback_leaves_no_partial_writes
  ✓ test_audit_event_polymorphic_integrity

server/tests/test_domain_models.py (9 tests)
  ✓ test_patient_model_valid
  ✓ test_patient_model_rejects_non_synthetic_mrn
  ✓ test_patient_model_rejects_missing_synthetic_name_tag
  ✓ test_follow_up_task_explicit_nulls
  ✓ test_follow_up_task_rejects_invalid_source_reference
  ✓ test_proposal_review_consistency_pending
  ✓ test_proposal_review_consistency_approved
  ✓ test_audit_event_creation
  ✓ test_source_reference_validation_against_plan

server/tests/test_hardening.py (10 tests)
  ✓ test_cannot_approve_rejected_proposal
  ✓ test_cannot_reject_approved_proposal
  ✓ test_reject_nonexistent_proposal
  ✓ test_high_concurrency_approval_deduplication
  ✓ test_audit_event_proposal_polymorphic_integrity
  ✓ test_rejection_of_fabricated_source_reference
  ✓ test_explicit_null_preservation
  ✓ test_api_rejects_non_synthetic_queries
  ✓ test_api_emergency_triage_refusal
  ✓ test_full_lifecycle_api_workflow

server/tests/test_mcp_streamable_http.py (3 tests)
  ✓ test_mcp_streamable_http_initialization
  ✓ test_mcp_server_lists_all_five_tools
  ✓ test_mcp_server_call_tools_end_to_end

server/tests/test_mcp_tools.py (10 tests)
  ✓ test_mcp_get_discharge_plan
  ✓ test_mcp_get_discharge_plan_rejects_non_synthetic
  ✓ test_mcp_list_tasks_and_filter
  ✓ test_mcp_propose_task_valid_source_reference
  ✓ test_mcp_propose_task_rejects_fabricated_source_reference
  ✓ test_mcp_approve_proposal_creates_task_and_audit
  ✓ test_mcp_approve_proposal_idempotent_retry
  ✓ test_mcp_approve_rejects_invalid_id
  ✓ test_mcp_get_audit_log
  ✓ test_mcp_approve_proposal_concurrent_attempts

server/tests/test_seeder.py (2 tests)
  ✓ test_seeder_populates_synthetic_data
  ✓ test_seeder_idempotency

============================= 50 passed in 7.90s =============================
```

---

## 8. Devpost Submission Checklist

- [x] **Primary Track Selected:** Amazon Alexa+
- [x] **Real Self-Hosted MCP Server:** Running over Streamable HTTP (`/mcp`) on official SDK (`2026-07-28` spec).
- [x] **No Fake Frontend Data:** Simulator UI consumes live FastAPI and FastMCP server.
- [x] **Approval Gating:** Tasks remain proposals until explicitly confirmed by the coordinator.
- [x] **Source Evidence Preserved:** Every task cites verbatim discharge plan text.
- [x] **Truthfulness & Missing Data:** Unstated dates/owners remain `null` and flagged for confirmation.
- [x] **Audit Trail:** Append-only ledger logs proposals, approvals, dismissals, and tasks.
- [x] **Safety Disclaimers:** Visible synthetic data notices in UI, API, and README.
- [x] **Reproducible Setup:** `.env.example` committed; clean virtual environment tested.
- [x] **Demo Video Ready:** Clear sub-3-minute walkthrough script provided.
- [x] **Zero Flaky Tests:** 50/50 tests passing consistently.

---

## 9. License

This project is licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.
