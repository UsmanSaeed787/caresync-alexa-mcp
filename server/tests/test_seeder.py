"""Tests for database seeder loading and idempotency."""

import aiosqlite
import pytest

from src.data.seeder import seed_synthetic_data
from src.db.repository import CareSyncRepository
from src.domain.enums import TaskStatus


async def test_seeder_populates_synthetic_data(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Verify seeder loads patient, plan, and initial tasks with varied states."""
    await seed_synthetic_data(db_path_override=test_db_path)

    repo = CareSyncRepository(test_db_conn)
    patient = await repo.get_patient("patient-synthetic-001")
    assert patient is not None
    assert patient.full_name == "Eleanor Vance [SYNTHETIC]"
    assert patient.mrn == "SYNTH-MRN-84920"
    assert patient.is_synthetic is True

    plan = await repo.get_discharge_plan_by_patient_id("patient-synthetic-001")
    assert plan is not None
    assert len(plan.source_excerpts) >= 3
    assert "cardiology_follow_up_date" in plan.explicit_missing_fields

    tasks = await repo.list_tasks("patient-synthetic-001")
    assert len(tasks) == 3

    statuses = {t.status for t in tasks}
    assert TaskStatus.COMPLETED in statuses
    assert TaskStatus.PENDING in statuses

    # Find the task with missing details
    unassigned_task = next(t for t in tasks if t.id == "task-synth-003")
    assert unassigned_task.owner is None
    assert unassigned_task.due_date is None
    assert unassigned_task.requires_human_confirmation is True


async def test_seeder_idempotency(test_db_path: str, test_db_conn: aiosqlite.Connection) -> None:
    """Running seeder multiple times must not duplicate records."""
    # Run seeder 3 times consecutively
    await seed_synthetic_data(db_path_override=test_db_path)
    await seed_synthetic_data(db_path_override=test_db_path)
    await seed_synthetic_data(db_path_override=test_db_path)

    async with test_db_conn.execute("SELECT COUNT(*) FROM patients;") as cursor:
        patient_count = (await cursor.fetchone())[0]
        assert patient_count == 1, "There must be exactly 1 patient"

    async with test_db_conn.execute("SELECT COUNT(*) FROM discharge_plans;") as cursor:
        plan_count = (await cursor.fetchone())[0]
        assert plan_count == 1, "There must be exactly 1 discharge plan"

    async with test_db_conn.execute("SELECT COUNT(*) FROM follow_up_tasks;") as cursor:
        task_count = (await cursor.fetchone())[0]
        assert task_count == 3, "There must be exactly 3 tasks after repeated seeding"
