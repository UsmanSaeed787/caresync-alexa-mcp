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
