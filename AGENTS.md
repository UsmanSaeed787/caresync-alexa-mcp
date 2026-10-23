# CareSync — Agent Instructions & Source of Truth

> **Status:** Hackathon MVP specification  
> **Primary track:** Amazon Alexa+  
> **Product:** CareSync — Alexa+ Care Coordination Agent  
> **Document role:** This file is the project's single source of truth (SOT).  
> **Rule:** If an implementation request conflicts with this file, stop and update this file/specification first. Do not silently expand scope.

## 1. Mission

Build a polished, working prototype that demonstrates how a voice-first assistant can turn a **synthetic hospital discharge plan** into a traceable, approval-gated follow-up workflow.

CareSync helps a care coordinator or authorized caregiver answer:

- What follow-up tasks are required by this sample discharge plan?
- Which tasks are still pending, completed, overdue, or missing an owner?
- Can I prepare a reminder or assign a follow-up task for approval?
- What changed, who approved it, and when?

**The product outcome:** a clear, auditable follow-up checklist with task status and ownership—not a chatbot that merely summarizes medical text.

## 2. Non-goals and safety boundaries

This is a hackathon prototype, not a clinical product or production electronic health record.

CareSync MUST NOT:
- diagnose, triage symptoms, recommend treatment, or estimate clinical risk;
- prescribe, discontinue, or change medication or dosage;
- make autonomous clinical decisions;
- contact real patients, providers, emergency services, or external systems;
- use real patient health information, credentials, or production EHR data;
- present generated information as a clinician-approved instruction.

CareSync MUST:
- use clearly labeled fictional/synthetic patient and discharge-plan data;
- preserve source text and distinguish extracted facts from inferred or missing information;
- mark uncertain or missing details for human review rather than inventing them;
- require explicit user approval before creating, assigning, or changing a task;
- show that reminders are simulated unless a real, authorized integration is later added;
- display a visible prototype/synthetic-data disclaimer in the UI and README.

If a user describes an emergency or asks for diagnosis/treatment, the app must not attempt clinical triage. It should state that this prototype cannot assess emergencies or provide medical advice and direct the person to local emergency services or a qualified healthcare professional as appropriate.

## 3. Target user and core workflow

**Primary user:** a care coordinator reviewing a fictional patient's discharge plan.

### Golden-path demo

1. Open the included synthetic patient and discharge plan.
2. Ask a question in the web simulator, e.g. “What follow-ups are still outstanding?”
3. The agent calls MCP tools to retrieve the plan and existing tasks.
4. The UI displays tasks with source evidence, due-date/owner status, and uncertainty flags.
5. Ask: “Prepare a follow-up task for the primary-care appointment.”
6. The agent proposes a task and explains which source text supports it. Missing due date or owner remains explicitly unset.
7. The user reviews and approves the proposal.
8. The system records the approved task and an audit event.
9. Ask again for outstanding follow-ups; the new task appears with its status.
10. The UI shows the audit trail and makes clear that any reminder is simulated.

The demo must show both a successful path and one uncertain/missing-information path.

## 4. Hackathon requirements

### Primary track: Alexa+

- Implement a real, self-hosted MCP server using **Streamable HTTP**.
- Use an MCP specification version **2025-11-25 or later**, verified against the SDK/server version and official documentation before implementation.
- The web simulator must invoke the MCP tools through the running server; do not fake tool results in the UI.
- If a real Alexa+ Preview integration is unavailable, describe the experience honestly as an Alexa+-style web simulation. Never claim it is connected to a real Alexa+ device/account.

### Optional mini-challenges

- **AWS Builder:** optional. Add an AWS service only if the core workflow is already reliable and the integration can be documented and demonstrated. A Bedrock call alone does not guarantee a prize.
- **Open Source:** optional. A license alone does not qualify. Make a genuine new project or meaningful public contribution during the event window and provide the required contribution/repository details.
- Prioritize a complete primary-track submission over optional prizes.

### Submission artifacts

- Public repository with an open-source license, or a private repository shared with the official hackathon reviewers as instructed by Devpost.
- README with architecture, setup, safety boundaries, and demo instructions.
- Working demo video in English, under three minutes.
- Accurate Devpost project description, track selections, and product/tool feedback.
- Friction log entries if applicable; record real issues and workarounds, never fabricate them.
- Verify the live Devpost deadline and submission state immediately before finalizing.

## 5. Architecture

Use a small, testable architecture:

- **Frontend:** Next.js + TypeScript + Tailwind CSS.
- **Backend/API:** Python + FastAPI.
- **MCP server:** Python FastMCP or the current supported MCP Python SDK, using Streamable HTTP.
- **Agent:** OpenAI Agents SDK or a compatible agent implementation. Keep the provider behind a small adapter so the workflow can be tested without paid model access.
- **Persistence:** SQLite for the time-boxed MVP; repository/service interfaces should allow PostgreSQL later. Do not add PostgreSQL unless it is needed and tested within the deadline.
- **Data:** bundled fictional JSON/SQLite seed data only.
- **Tests:** pytest for backend and tool logic; frontend build/type checks.
- **Deployment:** local demo first. Deploy only after the golden path works locally.

### Architectural rules

- Keep domain logic separate from HTTP routes, MCP tools, and model-provider code.
- The frontend must never connect directly to the database.
- Validate inputs at the API/MCP boundary.
- Use typed request/response models and stable error shapes.
- Keep task creation and state-changing actions approval-gated.
- Make the approval operation idempotent where practical; prevent accidental duplicate task creation.
- Do not log secrets or unnecessary health-related content.
- Put configuration in environment variables; commit only `.env.example`, never `.env`.
- No real credentials, patient data, or proprietary employer code.

## 6. Initial MCP tool contract

Keep the first version small. Tool names and schemas should be finalized in the Phase 1 spec before implementation.

1. `get_discharge_plan(patient_id)`
   - Read-only.
   - Returns synthetic plan summary, source excerpts, and explicit missing fields.

2. `list_follow_up_tasks(patient_id, status?)`
   - Read-only.
   - Returns task IDs, titles, status, owner/due-date fields, and source references.

3. `propose_follow_up_task(patient_id, source_reference, title, due_date?, owner?)`
   - Does not persist a task as approved.
   - Creates a pending proposal for human review.
   - Rejects unsupported or fabricated source references.

4. `approve_follow_up_task(proposal_id, approved_by)`
   - State-changing.
   - Must require an explicit approval action from the simulator UI.
   - Records the task and an audit event; repeated approval must not create duplicates.

5. `get_audit_log(patient_id)`
   - Read-only.
   - Returns relevant task/proposal events without exposing secrets.

Do not add arbitrary SQL tools, unrestricted file access, general-purpose shell execution, or a tool that can contact real people.

## 7. Data and domain rules

- Seed at least one clearly fictional patient and one discharge plan.
- Include a small, realistic set of follow-up tasks with varied states: pending, completed, and missing owner/due date.
- Each extracted/proposed task must retain a source reference or be marked “requires human confirmation.”
- Missing data is `null`/unknown, never guessed.
- Store timestamps in UTC and display them in the user's local timezone where practical.
- Use stable IDs and validate allowed task status transitions.
- Keep an append-only audit-event record for proposals, approvals, and task-status changes.
- Do not store more synthetic data than the demo needs.

## 8. UX requirements

The UI should feel like a focused professional care-coordination workspace, not a generic chat clone.

Required areas:
- **Patient context panel:** clearly fictional patient label and discharge-plan summary.
- **Conversation panel:** user prompt, assistant response, and visible tool activity.
- **Follow-up board:** task, status, owner, due date, source evidence, and uncertainty/missing-data indicators.
- **Approval panel:** proposed change, rationale/source, Approve and Reject actions.
- **Audit trail:** timestamped actions and outcomes.
- **System status:** MCP connection state and clear errors if the server is unavailable.
- **Safety label:** synthetic data / prototype / not for clinical decision-making.

Use accessible contrast, clear status labels, loading states, empty states, and recoverable errors. Never make approval buttons look pre-approved or hide the source of a proposed task.

## 9. Definition of done

The MVP is not done until all of the following are true:

- [ ] A fresh clone can be configured using the README and `.env.example`.
- [ ] The backend and MCP server start using documented commands.
- [ ] The UI invokes the running MCP server and shows real tool results.
- [ ] The golden path works from plan lookup through proposal, explicit approval, and audit entry.
- [ ] Missing/uncertain information is shown honestly; the system does not invent a due date or owner.
- [ ] Unapproved proposals do not appear as approved tasks.
- [ ] Repeated approval does not create duplicate tasks.
- [ ] Invalid IDs and malformed inputs return safe, understandable errors.
- [ ] Tests cover tool validation, approval gating, audit events, and duplicate prevention.
- [ ] Frontend build/type checks and backend tests pass.
- [ ] The README explains limitations and labels the data as synthetic.
- [ ] A sub-three-minute demo clearly shows the workflow and actual MCP tool calls.
- [ ] Devpost submission requirements and deadline are rechecked.

## 10. Time-box and priority order

**P0 — must ship**
1. Synthetic seed data and domain models.
2. Read-only plan/task tools.
3. Proposal → approval → audit workflow.
4. Streamable HTTP MCP server.
5. Functional simulator UI and golden-path demo.
6. Tests, README, environment example, and video.

**P1 — only after P0 works**
- Better visual polish and a second demo scenario.
- Model-provider integration improvements.
- Deployment and reliability improvements.

**P2 — cut if time is short**
- AWS Bedrock integration.
- Authentication and multi-tenant support.
- PostgreSQL migration.
- Notifications, real EHR integration, voice/audio streaming, and additional agents.

Do not sacrifice the working end-to-end workflow to add optional features.

## 11. Spec-driven development protocol

Work in this order:

1. `AGENTS.md` (this file) — product-level source of truth.
2. `specs/phase-1-foundation.md` — architecture, repo layout, environment, health checks, seed data, and acceptance criteria.
3. `specs/phase-2-mcp-workflow.md` — tool schemas and Streamable HTTP acceptance tests.
4. `specs/phase-3-simulator-ui.md` — screens and UI behavior.
5. `specs/phase-4-hardening-submission.md` — tests, demo script, README, and Devpost checklist.

For each phase:
- inspect the existing repository before changing files;
- report current state and conflicts with this SOT;
- implement only the approved phase;
- run the specified tests and report exact outcomes;
- list incomplete work and risks honestly;
- do not start the next phase until the current acceptance criteria pass or the user explicitly accepts a documented exception.

AI-generated code must be reviewed. Never claim tests passed unless they were actually run.

## 12. Decisions that must not drift

- Product name: **CareSync — Alexa+ Care Coordination Agent**.
- Primary track: **Alexa+**.
- Core outcome: **human-approved, traceable follow-up task coordination from a synthetic discharge plan**.
- Data: synthetic only.
- Integration: actual MCP tools over Streamable HTTP.
- Safety: no diagnosis, triage, treatment recommendations, medication changes, or real-world patient contact.
- Scope: one excellent end-to-end workflow over many incomplete features.
