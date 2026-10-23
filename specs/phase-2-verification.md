# CareSync — Final Phase 2 Verification Before Phase 3

Read `AGENTS.md`, `specs/phase-1-fixes.md`, and `specs/phase-2-mcp-workflow.md`. Inspect the actual code; do not rely on your previous completion report.

## Part A — Verify, do not assume

1. Inspect `server/requirements.txt` and the currently installed environment. Create a **separate clean virtual environment** and verify that all declared dependencies install successfully. Run `pip check` and the full test suite in that clean environment. Do not silently change pinned versions just to make the installation pass.
2. Verify the official MCP Python SDK API and protocol version supported by the installed package. Confirm that the mounted `/mcp` endpoint supports Streamable HTTP initialization, tool discovery, and actual tool calls—not just HTTP route responses.
3. Inspect all five MCP tools and verify their input validation, structured outputs, errors, and read-only versus state-changing behavior.
4. Verify source references against the correct patient's actual synthetic discharge plan. Ensure proposed titles, due dates, and owners cannot be fabricated or silently inferred when unsupported.
5. Verify approval is a deliberate, separate action. Confirm that pending proposals do not create active tasks, and that successful approval atomically creates the task and audit records. Test repeated and concurrent approval attempts for duplicate writes.
6. Inspect audit events for correct patient/entity association, chronology, and accurate action records. Confirm failed transactions leave no partial writes.
7. Verify all API and MCP query paths enforce the synthetic-data boundary.
8. Inspect `DeterministicAgentAdapter`. Clearly distinguish deterministic orchestration from actual LLM-based tool selection. Do not claim an LLM or Alexa+ integration exists unless it is implemented and tested.

## Part B — Report honestly

Return:
- Any real defects found and the exact fixes made.
- Clean-environment installation output, final dependency versions, `pip check`, and full test results.
- Evidence that all five MCP tools work through the HTTP transport.
- Tests for concurrent/repeated approval, source validation, and transaction rollback.
- Any remaining limitations, especially real LLM and Alexa+ integration.
- Exact commands to run the project from the repository root.

Do not claim production readiness or complete Alexa+ integration based on unit tests. Do not introduce unrelated features or change project scope.

After these checks pass, stop and prepare for Phase 3: the simulator UI connected to the actual backend and MCP workflow.