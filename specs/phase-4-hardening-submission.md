# Phase 4 Specification: Hardening, Verification & Submission Artifacts

> **Document Status:** Active Specification  
> **Phase:** 4 of 4 (Final)  
> **Source of Truth:** [AGENTS.md](file:///c:/Users/AL%20HAMD%20TRADERS/Desktop/Usman/projects/caresync-alexa-mcp/AGENTS.md)  
> **Mission:** Audit and harden existing implementation, verify edge cases, add hardening tests, create submission README, demo script, and Devpost checklist.

---

## 1. Objectives & Boundaries

Phase 4 does **not** rebuild existing functionality. It audits, hardens, and documents the existing implementation across:
1. **Approval & Rejection State Transitions:**
   - Explicit approval persists task, updates proposal to `APPROVED`, records `PROPOSAL_APPROVED` and `TASK_CREATED`.
   - Explicit rejection updates proposal to `REJECTED`, records `PROPOSAL_REJECTED`, and does **not** create a task.
   - Idempotent retries for approval and rejection.
   - Prohibiting illegal transitions: cannot approve a rejected proposal; cannot reject an approved proposal.
2. **Concurrent Approvals:**
   - Multi-worker or concurrent `asyncio` approval calls on the same proposal must be serialized safely with `BEGIN IMMEDIATE` / Compare-And-Swap (CAS), ensuring exactly one task is persisted.
3. **Audit Integrity:**
   - Polymorphic referential integrity: events must link to valid entities of the correct entity type and matching patient.
   - Append-only provenance: audit log reflects every state change in chronological order.
4. **Source Evidence & Ground Truth:**
   - Validation against fabricated or missing excerpts: `source_reference` must match genuine plan text.
   - Missing fields must remain explicitly `null` (never hallucinated or guessed).
5. **Robust Error Handling:**
   - Safe HTTP errors on non-synthetic IDs (`400 Bad Request`), unknown records (`404 Not Found`), and malformed inputs (`422 Unprocessable Entity`).
   - Clinical triage emergency refusal with safe non-clinical guidance.
6. **End-to-End Workflow Verification:**
   - Scripted automated E2E workflow exercising the live Next.js UI and backend.
7. **Submission Documentation:**
   - Root `README.md` meeting all Devpost / Amazon Alexa+ Hackathon criteria.
   - Sub-three-minute demo script.
   - Verified `.env.example` configurations.

---

## 2. Hardening Test Matrix

| Category | Test Case | Target Module | Expected Outcome |
| :--- | :--- | :--- | :--- |
| **Approval / Rejection** | Cannot approve rejected proposal | `server/tests/test_hardening.py` | `ValueError` / HTTP 400 |
| **Approval / Rejection** | Cannot reject approved proposal | `server/tests/test_hardening.py` | `ValueError` / HTTP 400 |
| **Approval / Rejection** | Reject non-existent proposal | `server/tests/test_hardening.py` | `ValueError` / HTTP 400 |
| **Concurrent Approvals** | High concurrency (5 tasks) | `server/tests/test_hardening.py` | Exactly 1 task created, 5 successes returning same task |
| **Audit Integrity** | Audit event with mismatched proposal patient | `server/tests/test_hardening.py` | `ValueError` ("does not match proposal patient") |
| **Missing Evidence** | Reject proposal with fabricated source excerpt | `server/tests/test_hardening.py` | `ValueError` ("fabricated or unverified") |
| **Missing Evidence** | Explicit nulls on missing dates/owners | `server/tests/test_hardening.py` | `due_date is None`, `owner is None`, `requires_human_confirmation is True` |
| **Error Handling** | Agent chat with non-synthetic patient | `server/tests/test_hardening.py` | HTTP 400 with synthetic data warning |
| **Error Handling** | Triage emergency prompt via API | `server/tests/test_hardening.py` | `safety_refusal: True`, emergency guidance returned |
| **Workflow E2E** | Live API end-to-end golden path | `server/tests/test_hardening.py` | Complete lifecycle: context -> list -> propose -> reject -> propose -> approve -> verify task -> verify audit |

---

## 3. Submission Documentation Requirements

1. **`README.md`**:
   - Executive Summary & Hackathon Track (Amazon Alexa+ Primary Track).
   - Real FastMCP Streamable HTTP implementation details (spec version 2026-07-28 / 2025-11-25+).
   - Core Workflow: Human-in-the-loop approval gating & synthetic hospital discharge coordination.
   - Non-goals & Safety Disclaimers (no clinical advice, no diagnosis/triage, synthetic data only).
   - Architecture Diagram (Next.js Simulator -> FastAPI -> FastMCP Streamable HTTP -> SQLite).
   - Getting Started (prerequisites, `.env.example`, PowerShell startup commands, test suite).
   - 3-Minute Demo Video Script.
   - Friction Log & Developer Feedback.
2. **Configuration**:
   - Root `.env.example` & `server/.env.example` verified with no committed secrets.

---

## 4. Definition of Phase 4 Done

- [x] Hardening test suite added in `server/tests/test_hardening.py`.
- [x] All existing tests (40/40) plus all new hardening tests pass 100%.
- [x] Full E2E workflow script verified against running backend and frontend.
- [x] Root `README.md` completed with architecture, demo script, setup guide, and safety boundaries.
- [x] Devpost submission checklist verified.
