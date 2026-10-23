# Phase 1 Specification: Foundation & Domain Core

> **Document Status:** Approved for Implementation  
> **Phase:** 1 of 4  
> **Source of Truth:** [AGENTS.md](file:///c:/Users/AL%20HAMD%20TRADERS/Desktop/Usman/projects/caresync-alexa-mcp/AGENTS.md)  
> **Implementation State:** Active Implementation

---

## 1. Objectives & Boundaries

Phase 1 establishes the reproducible architecture, directory structure, locked dependency management, domain models, minimal synthetic seed data, SQLite persistence layer with strict referential integrity and explicit transactions, and baseline FastAPI application with health checks and patient context endpoints.

### 1.1 In Scope for Phase 1
- **Repository Setup:** Git repository initialization and `.gitignore` setup preventing leaks of secrets, database files, virtual environments, or build artifacts.
- **Reproducible Dependencies:** Locked, tested Python dependencies without open-ended constraints, specifically tailored for Python 3.13.
- **Domain Modeling & Application Boundary Validation:** Pydantic v2 models (`Patient`, `DischargePlan`, `FollowUpTask`, `TaskProposal`, `AuditEvent`) strictly enforcing UTC timestamps, synthetic-only markers at the application boundary, and explicit nullability (missing due dates/owners remain `null`, never guessed).
- **Source Reference Validation:** `source_reference` must point to a non-empty, genuine excerpt from the patient's discharge plan or be flagged for human review.
- **Clinical Safety Boundaries:** Zero clinical decision-making, diagnosis, symptom triage, medication adjustments, or treatment recommendation logic. Synthetic data is treated strictly as auditable source text.
- **Minimal Synthetic Seed Data:** Exactly one clearly labeled fictional patient (`Eleanor Vance [SYNTHETIC]`), one discharge summary with verbatim excerpts, and three initial follow-up tasks demonstrating varied states (completed, pending with owner, pending with missing fields). All dates belong to a static, fictional demonstration scenario.
- **SQLite Persistence & Integrity:**
  - Foreign key constraints enabled per connection (`PRAGMA foreign_keys = ON;`).
  - Strict primary and unique constraints (`mrn UNIQUE`).
  - Check constraints for proposal review consistency (`PENDING` proposals must have null review fields; `APPROVED`/`REJECTED` must have non-null reviewer and timestamp).
  - Explicit, tested transaction handling (`await db.commit()` and `await db.rollback()`).
  - Idempotent seed ingestion that prevents duplicate records on repeat executions.
- **API Baseline:**
  - Configuration management via `pydantic-settings` and committed `.env.example`.
  - `GET /health` verifying service liveness, database connectivity, and synthetic data flags.
  - `GET /api/v1/context` providing the synthetic patient summary, source excerpts, and safety banner for the context panel.
- **Automated Testing:** Pytest suite covering domain validation, database schema constraints, foreign key enforcement, transaction rollback, proposal review consistency, seeder idempotency, and API endpoints.

### 1.2 Out of Scope for Phase 1 (Deferred to Later Phases)
- **MCP Server & Protocol (Deferred to Phase 2):** MCP Python SDK (`mcp`), FastMCP / ASGI Streamable HTTP transport, tool registrations (`get_discharge_plan`, `list_follow_up_tasks`, `propose_follow_up_task`, `approve_follow_up_task`, `get_audit_log`), and protocol specification verification (2025-11-25+).
- **Agent Reasoning & LLM Adapters (Deferred to Phase 2):** OpenAI Agents SDK or local deterministic mock agent adapter.
- **Simulator User Interface (Deferred to Phase 3):** Next.js 14+ frontend, Tailwind CSS workspace layout, approval panel, and audit log viewer.
- **Hardening & Devpost Submission (Deferred to Phase 4):** Video recording, production packaging, end-to-end demo scripts.

---

## 2. Environment & Reproducible Tooling

All commands are executed from the **repository root** (`c:\Users\AL HAMD TRADERS\Desktop\Usman\projects\caresync-alexa-mcp`).

| Tool / Runtime | Installed Version | Windows PowerShell Command Pattern | Verification |
| :--- | :--- | :--- | :--- |
| **Git** | 2.55.0.windows.5 | `git init` | `git status` |
| **Python** | 3.13.15 (`py`) | `py -m venv server\.venv` | `server\.venv\Scripts\python.exe --version` |
| **Pip** | 26.2.1 | `server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt` | `server\.venv\Scripts\python.exe -m pip list` |
| **Node.js** | v24.20.0 | *(Deferred to Phase 3)* | `node --version` |
| **npm** | 11.19.0 | *(Deferred to Phase 3; use `npm.cmd`)* | `npm.cmd --version` |

### 2.1 Reproducible Dependency-Locking Strategy
Phase 1 pins exact dependency versions verified against Python 3.13 in `server/requirements.txt`:

```text
# FastAPI & ASGI Web Server
fastapi==0.115.6
uvicorn[standard]==0.34.0

# Data Validation & Settings
pydantic==2.10.4
pydantic-settings==2.7.1

# SQLite Async Engine
aiosqlite==0.20.0

# Testing & HTTP Client
pytest==8.3.4
pytest-asyncio==0.25.0
httpx==0.28.1
```

---

## 3. Repository Layout (Phase 1 Target)

```
caresync-alexa-mcp/
├── .gitignore
├── AGENTS.md                          # Source of Truth
├── specs/
│   ├── phase-1-foundation.md          # This specification
│   ├── phase-2-mcp-workflow.md        # (Deferred to Phase 2)
│   ├── phase-3-simulator-ui.md        # (Deferred to Phase 3)
│   └── phase-4-hardening-submission.md# (Deferred to Phase 4)
├── server/
│   ├── .env.example                   # Committed template
│   ├── requirements.txt               # Exact pinned dependencies
│   ├── pytest.ini                     # pythonpath and test configuration
│   ├── src/
│   │   ├── __init__.py
│   │   ├── config.py                  # Pydantic Settings
│   │   ├── main.py                    # FastAPI application & lifecycle
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py               # TaskStatus, ProposalStatus, AuditAction
│   │   │   └── models.py              # Pydantic domain models with boundary validators
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── connection.py          # SQLite connection manager with PRAGMA foreign_keys & transaction helper
│   │   │   ├── schema.sql             # Strict DDL with FKs, checks, and unique indexes
│   │   │   └── repository.py          # Transactional repository operations
│   │   └── data/
│   │       ├── __init__.py
│   │       ├── seed_data.json         # Minimal synthetic dataset (static scenario)
│   │       └── seeder.py              # Idempotent database seeder
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                # Test DB fixtures with foreign keys enabled
│       ├── test_domain_models.py      # Model validation, boundary enforcement, null checks
│       ├── test_database.py           # Foreign keys, check constraints, uniqueness, rollback tests
│       ├── test_seeder.py             # Idempotency & seed data validation tests
│       └── test_api.py                # Tests for /health and /api/v1/context
└── simulator/                         # (Empty directory reserved for Phase 3)
```

---

## 4. Domain Models & Clinical Boundaries

### 4.1 Strict Safety Invariants & Application Boundary Validation
Per [AGENTS.md](file:///c:/Users/AL%20HAMD%20TRADERS/Desktop/Usman/projects/caresync-alexa-mcp/AGENTS.md) Section 2:
1. CareSync **does not** provide medical advice, triage, clinical decision-making, or medication changes.
2. Clinical notes and excerpts are stored and displayed as **unaltered source text** for auditability.
3. If an owner or due date is not stated in the source text, it must be stored as `None` (`null`), **never** guessed or defaulted.
4. Any record missing required follow-up details must set `requires_human_confirmation: True`.
5. **Synthetic Data Guardrails at Application Boundary:**
   - `Patient.is_synthetic` must be `True`. Models reject `is_synthetic=False` with a `ValueError`.
   - Patient MRNs must start with the prefix `SYNTH-`.
   - All models reject strings indicating real EHR origins or missing synthetic flags.
6. **Source Reference Validation:**
   - `source_reference` in `FollowUpTask` and `TaskProposal` must be a non-empty string and cannot consist merely of placeholders (e.g. `None`, `N/A`, `test`). It must cite a valid excerpt or reason requiring confirmation.

### 4.2 Enums (`server/src/domain/enums.py`)
- `TaskStatus`: `PENDING`, `COMPLETED`, `CANCELLED`
- `ProposalStatus`: `PENDING`, `APPROVED`, `REJECTED`
- `AuditAction`: `PROPOSAL_CREATED`, `PROPOSAL_APPROVED`, `PROPOSAL_REJECTED`, `TASK_CREATED`, `TASK_UPDATED`, `TASK_STATUS_CHANGED`

### 4.3 Pydantic Models (`server/src/domain/models.py`)
- **`Patient`**:
  - `id`: `str` (e.g., `"patient-synthetic-001"`)
  - `mrn`: `str` (Format: `SYNTH-MRN-XXXXX`)
  - `full_name`: `str`
  - `date_of_birth`: `str` (YYYY-MM-DD)
  - `is_synthetic`: `Literal[True] = True`
- **`DischargePlan`**:
  - `id`: `str`
  - `patient_id`: `str`
  - `admission_date`: `str` (YYYY-MM-DD, fictional static scenario)
  - `discharge_date`: `str` (YYYY-MM-DD, fictional static scenario)
  - `summary`: `str`
  - `source_text`: `str` (Verbatim discharge text)
  - `source_excerpts`: `list[dict[str, str]]` (Keyed excerpts, e.g., `[{"category": "PCP", "text": "..."}]`)
  - `explicit_missing_fields`: `list[str]` (e.g., `["cardiology_follow_up_date", "task_owner"]`)
  - `created_at`: `datetime` (UTC)
- **`FollowUpTask`**:
  - `id`: `str`
  - `patient_id`: `str`
  - `title`: `str`
  - `status`: `TaskStatus`
  - `due_date`: `Optional[str] = None`
  - `owner`: `Optional[str] = None`
  - `source_reference`: `str`
  - `requires_human_confirmation`: `bool = False`
  - `created_at`: `datetime` (UTC)
  - `updated_at`: `datetime` (UTC)
- **`TaskProposal`**:
  - `id`: `str`
  - `patient_id`: `str`
  - `title`: `str`
  - `due_date`: `Optional[str] = None`
  - `owner`: `Optional[str] = None`
  - `source_reference`: `str`
  - `status`: `ProposalStatus = ProposalStatus.PENDING`
  - `proposed_by`: `str`
  - `reviewed_by`: `Optional[str] = None`
  - `reviewed_at`: `Optional[datetime] = None`
  - `created_at`: `datetime` (UTC)
- **`AuditEvent`**:
  - `id`: `str`
  - `patient_id`: `str`
  - `action`: `AuditAction`
  - `entity_type`: `str` (`"task"` or `"proposal"`)
  - `entity_id`: `str`
  - `performed_by`: `str`
  - `details`: `dict[str, Any]`
  - `timestamp`: `datetime` (UTC)

---

## 5. Minimal Synthetic Seed Data Specification

File: `server/src/data/seed_data.json`

All clinical events and dates belong to a **static, fictional demonstration scenario** used strictly for illustrating follow-up workflows:
1. **Patient:** `Eleanor Vance [SYNTHETIC]` (DOB: `1952-08-14`, MRN: `SYNTH-MRN-84920`, `is_synthetic: true`).
2. **Discharge Plan:**
   - Summary: Synthetic post-discharge coordination plan following hospitalization for heart failure stabilization.
   - Scenario Dates: Admission `2026-10-14`, Discharge `2026-10-20`.
   - Verbatim Source Text: Standardized hospital discharge instructions outlining follow-up requirements.
   - Key Excerpts:
     - `PCP Follow-Up`: "Schedule follow-up appointment with primary care physician Dr. Sarah Jenkins within 7 days of discharge (by 2026-10-27)."
     - `Specialist Follow-Up`: "Follow up with outpatient cardiology clinic. Patient requires echocardiogram in 4 weeks." *(No specific date or owner provided)*.
     - `Lab Work`: "Order basic metabolic panel (BMP) in 10-14 days." *(No assigned owner)*.
   - Explicit Missing Fields: `["cardiology_follow_up_date", "lab_coordinator_owner"]`.
3. **Follow-Up Tasks (Initial States):**
   - **Task 1 (Completed):** "Medication reconciliation reviewed with patient prior to discharge" -> `status`: `COMPLETED`, `owner`: `Nurse Case Manager Rivera`, `due_date`: `2026-10-20`.
   - **Task 2 (Pending with Owner):** "Schedule primary care physician appointment with Dr. Sarah Jenkins" -> `status`: `PENDING`, `owner`: `Care Coordinator Alex`, `due_date`: `2026-10-27`.
   - **Task 3 (Missing Owner & Due Date):** "Schedule outpatient cardiology appointment and 4-week echocardiogram" -> `status`: `PENDING`, `owner`: `null`, `due_date`: `null`, `requires_human_confirmation`: `true`.

---

## 6. SQLite Schema, Integrity, and Transactions

### 6.1 Strict DDL (`server/src/db/schema.sql`)
```sql
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    mrn TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    date_of_birth TEXT NOT NULL,
    is_synthetic INTEGER NOT NULL DEFAULT 1 CHECK (is_synthetic = 1),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discharge_plans (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    admission_date TEXT NOT NULL,
    discharge_date TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_text TEXT NOT NULL,
    source_excerpts TEXT NOT NULL,
    explicit_missing_fields TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS follow_up_tasks (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'COMPLETED', 'CANCELLED')),
    due_date TEXT NULL,
    owner TEXT NULL,
    source_reference TEXT NOT NULL,
    requires_human_confirmation INTEGER NOT NULL DEFAULT 0 CHECK (requires_human_confirmation IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_proposals (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    title TEXT NOT NULL,
    due_date TEXT NULL,
    owner TEXT NULL,
    source_reference TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
    proposed_by TEXT NOT NULL,
    reviewed_by TEXT NULL,
    reviewed_at TEXT NULL,
    created_at TEXT NOT NULL,
    CONSTRAINT check_proposal_review_consistency CHECK (
        (status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR
        (status IN ('APPROVED', 'REJECTED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('task', 'proposal')),
    entity_id TEXT NOT NULL,
    performed_by TEXT NOT NULL,
    details TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_patient_id ON follow_up_tasks(patient_id);
CREATE INDEX IF NOT EXISTS idx_proposals_patient_id ON task_proposals(patient_id);
CREATE INDEX IF NOT EXISTS idx_audit_patient_id ON audit_events(patient_id);
```

### 6.2 Connection Management & Explicit Transaction Handling
In `aiosqlite`, connections do not implicitly manage multi-statement transactions with auto-rollback on arbitrary errors. Therefore:
1. Every connection issues `PRAGMA foreign_keys = ON;` on open.
2. An explicit transactional helper / context manager is implemented in `server/src/db/connection.py`:
   ```python
   @asynccontextmanager
   async def transaction(db: aiosqlite.Connection):
       try:
           yield db
           await db.commit()
       except Exception:
           await db.rollback()
           raise
   ```
3. Repository functions execute inside this transaction block, ensuring that if any step in a multi-operation workflow fails, changes are completely rolled back.
4. **Integrity Tests:**
   - Inserting an orphan task or plan with invalid `patient_id` raises `sqlite3.IntegrityError`.
   - Inserting an invalid proposal (e.g. `status = 'APPROVED'` with `reviewed_by = NULL`) violates `check_proposal_review_consistency` and raises `sqlite3.IntegrityError`.
   - Multi-statement failure rolls back the entire batch.

### 6.3 Idempotent Seeding (`server/src/data/seeder.py`)
- Seeder reads `seed_data.json` and inserts patient, plan, and initial tasks using `INSERT OR IGNORE` or checking entity existence.
- Repeated executions do not duplicate rows or alter existing state.

---

## 7. Baseline FastAPI Application & Endpoints

- **Entrypoint:** `server/src/main.py`
- **Lifespan Manager:**
  1. Initializes SQLite tables from `schema.sql`.
  2. Runs idempotent seeder if configured (`SEED_ON_STARTUP=True`).
- **Configuration (`server/src/config.py`):**
  - Uses `pydantic-settings` to load from environment or `server/.env`.
  - Default `DATABASE_URL`: `sqlite:///./caresync_local.db`
  - Default `SYNTHETIC_DATA_MODE`: `True`

### 7.1 Endpoints Specification

#### 1. `GET /health`
- **Status Code:** `200 OK`
- **Response Schema:**
  ```json
  {
    "status": "healthy",
    "service": "CareSync API",
    "synthetic_data_mode": true,
    "database": "connected",
    "version": "0.1.0"
  }
  ```

#### 2. `GET /api/v1/context`
- **Query Parameter:** `patient_id: str` (Defaults to `"patient-synthetic-001"`)
- **Status Code:** `200 OK` (or `404 Not Found` if patient does not exist)
- **Response Schema:**
  ```json
  {
    "patient": {
      "id": "patient-synthetic-001",
      "mrn": "SYNTH-MRN-84920",
      "full_name": "Eleanor Vance [SYNTHETIC]",
      "date_of_birth": "1952-08-14",
      "is_synthetic": true
    },
    "discharge_plan": {
      "id": "plan-synthetic-001",
      "patient_id": "patient-synthetic-001",
      "admission_date": "2026-10-14",
      "discharge_date": "2026-10-20",
      "summary": "Synthetic post-discharge coordination plan...",
      "explicit_missing_fields": ["cardiology_follow_up_date", "lab_coordinator_owner"]
    },
    "safety_disclaimer": "SYNTHETIC DEMO DATA ONLY. Not for clinical decision-making, diagnosis, or real patient care."
  }
  ```

---

## 8. Test Configuration & Import Resolution

To ensure imports like `from src.domain.models import Patient` resolve consistently from the repository root, `server/pytest.ini` is defined as:

```ini
[pytest]
testpaths = server/tests
pythonpath = server
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
```

All test commands run from the repository root:
`server\.venv\Scripts\python.exe -m pytest server\tests -v`

---

## 9. Concrete Implementation Tasks

- [ ] **Task 1.1: Git & Repository Initialization**
  - Run `git init`.
  - Write root `.gitignore` (ignoring `.venv`, `__pycache__`, `*.db`, `.env`, `node_modules`, `.next`, IDE configs).
- [ ] **Task 1.2: Environment & Locked Dependencies**
  - Create `server/requirements.txt` with exact pinned versions.
  - Create `server/.env.example`.
  - Run `py -m venv server\.venv`.
  - Install dependencies: `server\.venv\Scripts\python.exe -m pip install -r server\requirements.txt`.
- [ ] **Task 1.3: Domain Layer**
  - Create `server/src/domain/enums.py` (`TaskStatus`, `ProposalStatus`, `AuditAction`).
  - Create `server/src/domain/models.py` (Pydantic v2 schemas with boundary validators and explicit nulls).
- [ ] **Task 1.4: Minimal Synthetic Seed Data**
  - Create `server/src/data/seed_data.json` containing fictional patient Eleanor Vance, discharge plan, and 3 tasks for the static demo scenario.
- [ ] **Task 1.5: SQLite Schema & Connection Layer**
  - Create `server/src/db/schema.sql` (strict DDL with foreign keys, checks, review consistency, indexes).
  - Create `server/src/db/connection.py` ensuring `PRAGMA foreign_keys = ON;` and explicit `transaction` context manager.
  - Create `server/src/db/repository.py` with transactional CRUD operations.
- [ ] **Task 1.6: Idempotent Seeder**
  - Create `server/src/data/seeder.py` populating database idempotently from `seed_data.json`.
- [ ] **Task 1.7: FastAPI Application & Endpoints**
  - Create `server/src/config.py` (Pydantic Settings).
  - Create `server/src/main.py` with lifespan event, CORS, `GET /health`, and `GET /api/v1/context`.
- [ ] **Task 1.8: Pytest Suite**
  - Create `server/pytest.ini` and `server/tests/conftest.py` with an in-memory test database fixture.
  - Create `server/tests/test_domain_models.py` (model constraints, boundary validators, explicit nullability).
  - Create `server/tests/test_database.py` (foreign keys, review consistency, uniqueness, transaction rollback).
  - Create `server/tests/test_seeder.py` (idempotency, seed counts, field integrity).
  - Create `server/tests/test_api.py` (endpoints `/health` and `/api/v1/context`, 404 handling).
- [ ] **Task 1.9: Execution & Verification**
  - Run full test suite: `server\.venv\Scripts\python.exe -m pytest server\tests -v`.

---

## 10. Concrete Acceptance Criteria & Verification Matrix

| ID | Criterion | Verification Method / Command | Expected Result |
| :--- | :--- | :--- | :--- |
| **AC-1.1** | Git repository initialized; `.gitignore` strictly excludes secrets, `.env`, `.db` files, `.venv`, and build artifacts. Source code files may remain untracked during local development. | `git check-ignore -v server/.env server/caresync_local.db server/.venv/bin` | All prohibited patterns match `.gitignore`. |
| **AC-1.2** | Exact pinned dependencies installed without version conflicts under Python 3.13. | `server\.venv\Scripts\python.exe -m pip check` | Returns code 0: `No broken requirements found.` |
| **AC-1.3** | Domain models strictly require `is_synthetic: true` at application boundary and preserve `null` for missing dates/owners without guessing. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_domain_models.py -v` | All domain model unit tests pass with 100% assertions satisfied. |
| **AC-1.4** | Foreign key constraints are enforced on all tables; inserting orphan records raises `sqlite3.IntegrityError`. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_database.py -k test_foreign_key_enforcement -v` | Test passes, confirming `PRAGMA foreign_keys = ON;` is active. |
| **AC-1.5** | Check constraints enforce review consistency on proposals (`PENDING` requires null reviewer; `APPROVED`/`REJECTED` requires reviewer). | `server\.venv\Scripts\python.exe -m pytest server\tests\test_database.py -k test_proposal_review_consistency -v` | Test passes, confirming consistency constraint holds. |
| **AC-1.6** | Database transactions are atomic; failures midway through multi-step operations roll back completely. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_database.py -k test_transaction_rollback -v` | Test passes, confirming zero orphaned rows after failure. |
| **AC-1.7** | Seeder is strictly idempotent; running it multiple times does not duplicate patients, plans, or tasks. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_seeder.py -k test_seeder_idempotency -v` | Row counts remain exactly 1 patient, 1 plan, 3 tasks after duplicate runs. |
| **AC-1.8** | `GET /health` returns 200 with `status: "healthy"` and `synthetic_data_mode: true`. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_api.py -k test_health_endpoint -v` | Returns 200 OK with expected JSON payload. |
| **AC-1.9** | `GET /api/v1/context` returns 200 with patient, plan summary, and safety disclaimer; returns 404 on invalid patient ID. | `server\.venv\Scripts\python.exe -m pytest server\tests\test_api.py -k test_context_endpoint -v` | Returns 200 OK for valid patient, 404 for unknown patient ID. |
| **AC-1.10** | Zero clinical triage, diagnostic, or medication adjustment logic is present. | Code audit of `server/src/`. | Pure coordination and tracking data structures only. |
