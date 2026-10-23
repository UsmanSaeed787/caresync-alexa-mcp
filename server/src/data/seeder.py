"""Idempotent database seeder for synthetic CareSync demonstration data."""

import json
from pathlib import Path
from typing import Optional
import aiosqlite

from src.db.connection import get_db
from src.db.repository import CareSyncRepository
from src.domain.enums import TaskStatus
from src.domain.models import DischargePlan, FollowUpTask, Patient

SEED_FILE_PATH = Path(__file__).parent / "seed_data.json"


async def seed_synthetic_data(db_path_override: Optional[str] = None) -> None:
    """Populate database idempotently with synthetic patient, discharge plan, and initial tasks."""
    with open(SEED_FILE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    patient_data = data["patient"]
    plan_data = data["discharge_plan"]
    tasks_data = data.get("tasks", [])

    patient = Patient(
        id=patient_data["id"],
        mrn=patient_data["mrn"],
        full_name=patient_data["full_name"],
        date_of_birth=patient_data["date_of_birth"],
        is_synthetic=patient_data["is_synthetic"],
    )

    plan = DischargePlan(
        id=plan_data["id"],
        patient_id=plan_data["patient_id"],
        admission_date=plan_data["admission_date"],
        discharge_date=plan_data["discharge_date"],
        summary=plan_data["summary"],
        source_text=plan_data["source_text"],
        source_excerpts=plan_data["source_excerpts"],
        explicit_missing_fields=plan_data["explicit_missing_fields"],
    )

    async with get_db(db_path_override) as db:
        repo = CareSyncRepository(db)

        # 1. Idempotently insert patient
        existing_patient = await repo.get_patient(patient.id)
        if not existing_patient:
            await repo.create_patient(patient)

        # 2. Idempotently insert discharge plan
        existing_plan = await repo.get_discharge_plan_by_patient_id(patient.id)
        if not existing_plan:
            await repo.create_discharge_plan(plan)

        # 3. Idempotently insert tasks
        for item in tasks_data:
            existing_task = await repo.get_task(item["id"])
            if not existing_task:
                task = FollowUpTask(
                    id=item["id"],
                    patient_id=item["patient_id"],
                    title=item["title"],
                    status=TaskStatus(item["status"]),
                    due_date=item.get("due_date"),
                    owner=item.get("owner"),
                    source_reference=item["source_reference"],
                    requires_human_confirmation=item.get("requires_human_confirmation", False),
                )
                await repo.create_task(task)
