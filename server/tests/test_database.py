"""Database tests for foreign keys, check constraints, uniqueness, and transaction rollback."""

import sqlite3
from datetime import datetime, timezone
import aiosqlite
import pytest

from src.db.connection import transaction
from src.db.repository import CareSyncRepository
from src.domain.enums import ProposalStatus, TaskStatus
from src.domain.models import FollowUpTask, Patient


async def test_foreign_key_enforcement(test_db_conn: aiosqlite.Connection) -> None:
    """Inserting a task referencing a non-existent patient must fail referential integrity."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with pytest.raises(sqlite3.IntegrityError):
        await test_db_conn.execute(
            """
            INSERT INTO follow_up_tasks (
                id, patient_id, title, status, due_date, owner, source_reference,
                requires_human_confirmation, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "task-orphan-001",
                "non-existent-patient-999",
                "Orphan Task",
                "PENDING",
                None,
                None,
                "Valid excerpt text here.",
                0,
                now_iso,
                now_iso,
            ),
        )


async def test_proposal_review_consistency(test_db_conn: aiosqlite.Connection) -> None:
    """Check constraint prevents APPROVED proposal without reviewed_by and reviewed_at."""
    # First insert a valid patient
    now_iso = datetime.now(timezone.utc).isoformat()
    await test_db_conn.execute(
        """
        INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
        VALUES (?, ?, ?, ?, 1, ?);
        """,
        ("patient-synth-test", "SYNTH-MRN-TEST", "Test Patient [SYNTHETIC]", "1980-01-01", now_iso),
    )
    await test_db_conn.commit()

    # Attempt inserting an APPROVED proposal without review metadata
    with pytest.raises(sqlite3.IntegrityError):
        await test_db_conn.execute(
            """
            INSERT INTO task_proposals (
                id, patient_id, title, due_date, owner, source_reference,
                status, proposed_by, reviewed_by, reviewed_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "prop-invalid-001",
                "patient-synth-test",
                "Unreviewed approval",
                None,
                None,
                "Excerpt source",
                "APPROVED",
                "agent",
                None,  # reviewed_by is NULL -> violates CHECK constraint!
                None,  # reviewed_at is NULL -> violates CHECK constraint!
                now_iso,
            ),
        )


async def test_patient_mrn_uniqueness(test_db_conn: aiosqlite.Connection) -> None:
    """Duplicate MRN values must violate UNIQUE constraint."""
    now_iso = datetime.now(timezone.utc).isoformat()
    await test_db_conn.execute(
        """
        INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
        VALUES (?, ?, ?, ?, 1, ?);
        """,
        ("patient-1", "SYNTH-MRN-UNIQUE", "Patient One [SYNTHETIC]", "1970-01-01", now_iso),
    )
    await test_db_conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        await test_db_conn.execute(
            """
            INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
            VALUES (?, ?, ?, ?, 1, ?);
            """,
            ("patient-2", "SYNTH-MRN-UNIQUE", "Patient Two [SYNTHETIC]", "1975-01-01", now_iso),
        )


async def test_transaction_rollback(test_db_conn: aiosqlite.Connection) -> None:
    """If an error occurs within transaction block, preceding changes must be rolled back."""
    now_iso = datetime.now(timezone.utc).isoformat()
    patient_id = "patient-rollback-test"

    with pytest.raises(RuntimeError):
        async with transaction(test_db_conn):
            await test_db_conn.execute(
                """
                INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
                VALUES (?, ?, ?, ?, 1, ?);
                """,
                (patient_id, "SYNTH-MRN-ROLLBACK", "Rollback Patient [SYNTHETIC]", "1960-05-10", now_iso),
            )
            # Simulate unexpected failure midway through the transaction
            raise RuntimeError("Forced simulation error triggering rollback")

    # Verify that the patient was NOT saved
    async with test_db_conn.execute("SELECT id FROM patients WHERE id = ?;", (patient_id,)) as cursor:
        row = await cursor.fetchone()
        assert row is None, "Patient must have been rolled back completely"


async def test_multistep_transaction_rollback_leaves_no_partial_writes(test_db_conn: aiosqlite.Connection) -> None:
    """Multi-step operation (patient + task + proposal) must leave zero partial writes on failure."""
    now_iso = datetime.now(timezone.utc).isoformat()
    pid = "patient-multistep-test"
    tid = "task-multistep-test"
    propid = "prop-multistep-test"

    with pytest.raises(ValueError):
        async with transaction(test_db_conn):
            # Step 1: Insert patient
            await test_db_conn.execute(
                """
                INSERT INTO patients (id, mrn, full_name, date_of_birth, is_synthetic, created_at)
                VALUES (?, ?, ?, ?, 1, ?);
                """,
                (pid, "SYNTH-MRN-MULTI", "Multi Test [SYNTHETIC]", "1972-01-01", now_iso),
            )
            # Step 2: Insert task
            await test_db_conn.execute(
                """
                INSERT INTO follow_up_tasks (
                    id, patient_id, title, status, due_date, owner, source_reference,
                    requires_human_confirmation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (tid, pid, "Task 1", "PENDING", None, None, "Valid source text", 0, now_iso, now_iso),
            )
            # Step 3: Insert proposal
            await test_db_conn.execute(
                """
                INSERT INTO task_proposals (
                    id, patient_id, title, due_date, owner, source_reference,
                    status, proposed_by, reviewed_by, reviewed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (propid, pid, "Proposal 1", None, None, "Valid source", "PENDING", "agent", None, None, now_iso),
            )
            # Step 4: Injected failure
            raise ValueError("Simulated unexpected failure during multi-step operation")

    # Verify zero partial writes across all tables
    for table, item_id in [("patients", pid), ("follow_up_tasks", tid), ("task_proposals", propid)]:
        async with test_db_conn.execute(f"SELECT id FROM {table} WHERE id = ?;", (item_id,)) as cursor:
            assert await cursor.fetchone() is None, f"{table} should have no partial writes"


async def test_audit_event_polymorphic_integrity(test_db_conn: aiosqlite.Connection) -> None:
    """Audit events must reference existing entities and reject cross-patient associations."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    repo = CareSyncRepository(test_db_conn)

    # Setup patient A and patient B
    await test_db_conn.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, 1, ?);",
        ("patient-synth-a", "SYNTH-MRN-AAA", "Patient A [SYNTHETIC]", "1960-01-01", now_iso),
    )
    await test_db_conn.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, 1, ?);",
        ("patient-synth-b", "SYNTH-MRN-BBB", "Patient B [SYNTHETIC]", "1965-01-01", now_iso),
    )
    # Task belongs to patient A
    await test_db_conn.execute(
        """
        INSERT INTO follow_up_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        ("task-a-1", "patient-synth-a", "Task A", "PENDING", None, None, "Valid reference text", 0, now_iso, now_iso),
    )
    await test_db_conn.commit()

    from src.domain.enums import AuditAction
    from src.domain.models import AuditEvent

    # 1. Non-existent task reference raises ValueError
    with pytest.raises(ValueError) as exc_info:
        await repo.record_audit_event(
            AuditEvent(
                id="audit-fake-task",
                patient_id="patient-synth-a",
                action=AuditAction.TASK_CREATED,
                entity_type="task",
                entity_id="task-nonexistent",
                performed_by="user",
            )
        )
    assert "non-existent task" in str(exc_info.value)

    # 2. Cross-patient mismatch: event claims patient B, but task belongs to patient A
    with pytest.raises(ValueError) as exc_info:
        await repo.record_audit_event(
            AuditEvent(
                id="audit-cross-patient",
                patient_id="patient-synth-b",  # Wrong patient!
                action=AuditAction.TASK_UPDATED,
                entity_type="task",
                entity_id="task-a-1",
                performed_by="user",
            )
        )
    assert "does not match task patient" in str(exc_info.value)

    # 3. Legitimate audit event succeeds
    valid_event = await repo.record_audit_event(
        AuditEvent(
            id="audit-valid-1",
            patient_id="patient-synth-a",
            action=AuditAction.TASK_CREATED,
            entity_type="task",
            entity_id="task-a-1",
            performed_by="user",
            details={"notes": "created"},
            timestamp=now,
        )
    )
    assert valid_event.id == "audit-valid-1"

