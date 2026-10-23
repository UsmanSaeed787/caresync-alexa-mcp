# Phase 3 Specification: CareSync Simulator UI

> **Document Status:** Active Specification  
> **Phase:** 3 of 4  
> **Source of Truth:** [AGENTS.md](file:///c:/Users/AL%20HAMD%20TRADERS/Desktop/Usman/projects/caresync-alexa-mcp/AGENTS.md)  
> **Implementation Target:** `simulator/` directory (Next.js 14+ / TypeScript / Tailwind CSS)

---

## 1. Objectives & Boundaries

Phase 3 builds a focused, professional care-coordination workspace that connects directly to the running FastAPI + Streamable HTTP MCP backend. There is **zero fake or client-only mock data**; every panel reflects live backend state and actual MCP tool calls.

### 1.1 In Scope for Phase 3
- **Next.js + TypeScript + Tailwind CSS Frontend in `simulator/`**:
  - Scaffolded with App Router, TypeScript, and clean Vanilla CSS / Tailwind styling.
- **Connected Panels (Live Backend API Integration)**:
  1. **Top Banner & Safety Label:**
     - Explicit banner: "CareSync — Alexa+ Care Coordination Simulation (Synthetic Data Only - Not for Medical Use)".
     - System Status pill displaying real-time MCP and Backend connection state (`/health`).
  2. **Patient Context Panel (`/api/v1/context`):**
     - Patient banner: Eleanor Vance [SYNTHETIC], MRN `SYNTH-MRN-84920`, DOB `1952-08-14`.
     - Admission & discharge dates (`2026-10-14` to `2026-10-20`).
     - Discharge summary overview and highlighted missing fields (`cardiology_follow_up_date`, `lab_coordinator_owner`).
     - Expandable source excerpts viewer showing the verified discharge text.
  3. **Follow-Up Board (`/api/v1/tasks`):**
     - Interactive checklist categorized by status (`PENDING`, `COMPLETED`).
     - Clear badges for owner and due date (explicitly displaying "Unassigned" and "Unset" when null).
     - "Human Review Required" warning badge for tasks with missing details.
     - Clickable "Source Evidence" popup/drawer showing verbatim discharge excerpt.
  4. **Conversation Panel (`/api/v1/agent/chat`):**
     - Voice/Alexa+-style conversational interface.
     - Quick-prompt buttons for the golden path ("What follow-ups are still outstanding?", "Prepare a follow-up task for the primary-care appointment", "Show audit trail").
     - Live assistant responses with collapsible **MCP Tool Activity** pills displaying tool name, arguments, and return payload.
  5. **Approval Panel (`/api/v1/tasks/approve`):**
     - Explicit approval staging area when a proposal is generated.
     - Displays proposed title, due date, owner, and source evidence.
     - "Approve Task" action button and "Dismiss" action.
     - Idempotent: displays confirmed status upon approval.
  6. **Audit Trail (`/api/v1/audit`):**
     - Live chronological timeline of events (`PROPOSAL_CREATED`, `PROPOSAL_APPROVED`, `TASK_CREATED`).
     - Displays actor, timestamp, entity type, and structured payload.
- **Zero Regressions:**
  - Backend and MCP test suite remains intact (39/39 passing).

### 1.2 Out of Scope for Phase 3
- Production EHR / FHIR integration.
- Physical Alexa+ hardware connection (honest web simulation).
- Video recording and Devpost markdown write-up (Phase 4).

---

## 2. API Connection Contracts

| Endpoint | Method | Purpose in UI |
| :--- | :--- | :--- |
| `http://127.0.0.1:8000/health` | `GET` | System status badge & MCP connection status. |
| `http://127.0.0.1:8000/api/v1/context?patient_id=patient-synthetic-001` | `GET` | Patient Context Panel & source text. |
| `http://127.0.0.1:8000/api/v1/tasks?patient_id=patient-synthetic-001` | `GET` | Follow-Up Board checklist & details. |
| `http://127.0.0.1:8000/api/v1/agent/chat` | `POST` | Conversation Panel turn execution & MCP tool tracing. |
| `http://127.0.0.1:8000/api/v1/tasks/approve` | `POST` | Approval Panel explicit task approval. |
| `http://127.0.0.1:8000/api/v1/audit?patient_id=patient-synthetic-001` | `GET` | Audit Trail chronological log. |

---

## 3. UI/UX Design System & Tokens

- **Aesthetic:** Professional clinical coordination dashboard (Slate, Indigo, Emerald for completed, Amber for pending review, Rose for safety disclaimers).
- **Typography:** Modern clean sans-serif (Inter / system fallback).
- **Micro-interactions:** Smooth transition on approval, tool expansion drawers, loading spinners.
- **Accessibility:** WCAG AA contrast ratio, keyboard navigability, clear aria-labels on approval actions.

---

## 4. Testable Acceptance Criteria (Definition of Phase 3 Done)

| ID | Criterion | Verification Method |
| :--- | :--- | :--- |
| **AC-3.1** | Simulator boots cleanly on `http://localhost:3000` without TypeScript or bundle errors. | `npm.cmd run build` in `simulator/` exits with code 0. |
| **AC-3.2** | UI fetches live patient context from `/api/v1/context` and displays "Eleanor Vance [SYNTHETIC]". | Patient banner displays correct synthetic MRN and dates from backend. |
| **AC-3.3** | Follow-Up Board displays real tasks from `/api/v1/tasks`; unassigned owners/dates explicitly render as "Unassigned" / "Unset" (never guessed). | Visual confirmation and task status checks. |
| **AC-3.4** | Conversation panel sends prompts to `/api/v1/agent/chat` and renders tool calls with inspectable arguments and results. | Prompt "What follow-ups are still outstanding?" shows `get_discharge_plan` and `list_follow_up_tasks` pills. |
| **AC-3.5** | Proposing a task presents an explicit Approval Panel with source evidence; task is **not** on active board until "Approve" is clicked. | Golden-path walkthrough step 5-7. |
| **AC-3.6** | Approving a task posts to `/api/v1/tasks/approve`, refreshes the Follow-Up Board to show the new task, and appends a `TASK_CREATED` audit event. | Golden-path walkthrough step 8-9. |
| **AC-3.7** | Clinical emergency prompts trigger prominent safety banner refusing medical advice. | Prompt "patient has severe chest pain" displays emergency guidance. |
| **AC-3.8** | Existing backend tests continue passing 100%. | `server\.venv\Scripts\python.exe -m pytest server\tests -v` returns 39 passed. |
