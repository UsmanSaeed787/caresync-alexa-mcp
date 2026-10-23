# CareSync — Phase 1 Targeted Verification + Phase 2 Implementation

Read `AGENTS.md`, `specs/phase-1-foundation.md`, and the existing Phase 1 code before proceeding.

## Part A — Targeted verification

Phase 1 reportedly has 16 passing tests. Do not rewrite working code or expand the scope.

Inspect and verify these specific points:

1. **Transactions:** Confirm the `aiosqlite` transaction helper explicitly commits on success and rolls back on failure. Add or fix a test proving that a multi-step operation leaves no partial writes after an injected failure.
2. **Source references:** Confirm that `source_reference` resolves to an actual source excerpt or section, rather than merely passing a string-format validator.
3. **Audit integrity:** Verify that audit events reference existing entities and cannot associate an event with the wrong patient. Use appropriate validation for the polymorphic task/proposal reference.
4. **Synthetic-only boundary:** Verify that non-synthetic records are rejected through application validation, not just SQLite constraints.
5. **Verification accuracy:** Run the full Phase 1 test suite, report the actual results, and reconcile the acceptance-criteria numbering in the specification.

Fix only genuine defects in these areas. Do not add unrelated features. Once these checks pass, proceed directly to Phase 2.

## Part B — Implement Phase 2: MCP workflow

Follow `AGENTS.md` as the source of truth. Read the official documentation for the installed, compatible MCP Python SDK version before implementing the server. Use Streamable HTTP, not legacy SSE.

Implement the five required MCP tools:

- `get_discharge_plan(patient_id)` — read-only.
- `list_follow_up_tasks(patient_id, status?)` — read-only.
- `propose_follow_up_task(patient_id, source_reference, title, due_date?, owner?)` — create a pending proposal; do not create an approved task.
- `approve_follow_up_task(proposal_id, approved_by)` — explicitly approve a pending proposal, persist the task, and record audit events atomically.
- `get_audit_log(patient_id)` — read-only.

### Mandatory workflow requirements

1. Reuse the existing domain models, repository, and SQLite database. Do not replace the persistence layer.
2. Never invent missing dates, owners, or source evidence.
3. Validate patient IDs, proposal IDs, and source references.
4. Require explicit human approval before a proposal becomes a persisted follow-up task.
5. Make approval safe to retry: a repeated approval must not create duplicate tasks or duplicate approval events.
6. Ensure task creation and its corresponding audit events succeed or fail atomically.
7. Return structured, predictable tool results and useful errors.
8. Keep all data synthetic. Do not add diagnosis, triage, treatment recommendations, medication changes, real patient contact, or real EHR integrations.
9. Do not add PostgreSQL, Docker, authentication infrastructure, or optional features during this phase.

### Agent integration

Implement the smallest agent adapter that supports the approved golden-path demonstration. Prefer the OpenAI Agents SDK if it integrates cleanly with the available environment. If credentials, network access, or integration complexity block reliable execution, implement a deterministic mock adapter behind the same interface and document the limitation. Do not pretend a mock is a live LLM.

### Required tests

Test the MCP tools and end-to-end workflow, including:

- Reading the synthetic discharge plan and existing tasks.
- Proposing a task with a valid source reference.
- Rejecting an invalid source reference.
- Confirming a proposal remains pending until explicit approval.
- Approving a proposal and verifying task persistence and audit events.
- Retrying approval without duplicate tasks or events.
- Rejecting invalid IDs and repeated or rejected proposal approvals.
- Ensuring failures roll back all writes in the transaction.
- Confirming missing owner/date values remain null.
- Verifying the MCP server is reachable over Streamable HTTP and its tools can be called.

## Completion report

When finished, provide:

1. Files created or modified.
2. MCP SDK version and official API/protocol references used.
3. Exact commands to start the API and MCP server.
4. Actual test results, including failures.
5. A demonstrated tool-call sequence from reading the plan through approval and audit verification.
6. Any unresolved limitations or blockers.

Do not claim Phase 2 is complete until the MCP tools are callable and the approval workflow passes its tests. Keep the implementation focused on a reliable hackathon demo.