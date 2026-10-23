"""Validation of source references against actual synthetic discharge plans."""

import re
from typing import Optional
from src.domain.models import DischargePlan


def _normalize(text: str) -> str:
    """Normalize whitespace and lowercase for reliable excerpt matching."""
    return re.sub(r"\s+", " ", text).strip().lower()


def validate_source_reference(source_reference: str, plan: DischargePlan) -> bool:
    """Verify that source_reference resolves to an actual excerpt, category, or text in the discharge plan.
    
    Rejects unsupported or fabricated source references.
    """
    if not source_reference:
        return False

    ref_norm = _normalize(source_reference)
    if len(ref_norm) < 5 or ref_norm in {"none", "n/a", "null", "test", "todo"}:
        return False

    # 1. Check if reference is contained in the verbatim source text
    plan_text_norm = _normalize(plan.source_text)
    if ref_norm in plan_text_norm:
        return True

    # 2. Check if reference matches or is contained in any specific excerpt
    for excerpt in plan.source_excerpts:
        excerpt_text = excerpt.get("text", "")
        excerpt_category = excerpt.get("category", "")

        excerpt_text_norm = _normalize(excerpt_text)
        excerpt_category_norm = _normalize(excerpt_category)

        if ref_norm in excerpt_text_norm or excerpt_text_norm in ref_norm:
            return True
        if excerpt_category_norm and (ref_norm in excerpt_category_norm or excerpt_category_norm in ref_norm):
            return True

    # 3. Check against explicit missing fields mention
    for field in plan.explicit_missing_fields:
        if _normalize(field) in ref_norm:
            return True

    return False
