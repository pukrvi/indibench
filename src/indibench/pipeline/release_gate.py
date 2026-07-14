"""Evidence gates that prevent candidates becoming an official release.

S2/S3 establish answer-key validity and frontier difficulty. They do not
replace source provenance (S0) or human audit evidence (S4).
"""

import json
import math
from collections import defaultdict
from pathlib import Path

from indibench.pipeline.s0_corpus import SourceDocument
from indibench.pipeline.s4_spotcheck import AuditVerdict, DEFAULT_SAMPLE_RATE
from indibench.schema import CandidateDraft, Tag


class ReleaseEvidenceError(ValueError):
    """A proposed release is missing required S0 or S4 evidence."""


def load_audit_verdicts(path: Path) -> dict[str, AuditVerdict]:
    """Load JSONL audits and reject conflicting duplicate verdicts."""
    verdicts: dict[str, AuditVerdict] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        verdict = AuditVerdict(**json.loads(line))
        existing = verdicts.get(verdict.item_id)
        if existing and existing != verdict:
            raise ReleaseEvidenceError(
                f"{path}:{lineno}: conflicting audit verdict for {verdict.item_id}"
            )
        verdicts[verdict.item_id] = verdict
    if not verdicts:
        raise ReleaseEvidenceError(f"{path}: audit file is empty")
    return verdicts


def require_release_evidence(
    drafts: list[CandidateDraft],
    sources: dict[str, SourceDocument],
    verdicts: dict[str, AuditVerdict],
) -> None:
    """Enforce S0 provenance plus S4 human-audit evidence.

    Each item needs a registered matching-language/domain source. Each safety
    item needs a passing audit; every other language×domain cell needs at
    least ceil(10%) passing audits.
    """
    missing_source: list[str] = []
    mismatched_source: list[str] = []
    failed_safety: list[str] = []
    cells: dict[tuple[str, str], list[CandidateDraft]] = defaultdict(list)

    for draft in drafts:
        if not draft.source_document_id:
            missing_source.append(draft.id or "<unassembled>")
        else:
            source = sources.get(draft.source_document_id)
            if source is None:
                missing_source.append(f"{draft.id} ({draft.source_document_id})")
            elif source.language != draft.language or source.domain != draft.domain:
                mismatched_source.append(draft.id or "<unassembled>")
        cells[(draft.language.value, draft.domain.value)].append(draft)
        if Tag.SAFETY in draft.tags:
            verdict = verdicts.get(draft.id or "")
            if not verdict or not (verdict.key_correct and verdict.question_well_formed):
                failed_safety.append(draft.id or "<unassembled>")

    if missing_source:
        raise ReleaseEvidenceError(
            "S0 source evidence missing for " + ", ".join(missing_source[:10]) +
            (" …" if len(missing_source) > 10 else "")
        )
    if mismatched_source:
        raise ReleaseEvidenceError(
            "S0 source language/domain mismatch for " + ", ".join(mismatched_source[:10])
        )
    if failed_safety:
        raise ReleaseEvidenceError(
            "S4 mandatory safety audit missing/failed for " + ", ".join(failed_safety[:10])
        )

    insufficient: list[str] = []
    for cell, cell_drafts in sorted(cells.items()):
        required = max(1, math.ceil(len(cell_drafts) * DEFAULT_SAMPLE_RATE))
        passing = sum(
            1
            for draft in cell_drafts
            if (verdict := verdicts.get(draft.id or ""))
            and verdict.key_correct
            and verdict.question_well_formed
        )
        if passing < required:
            insufficient.append(f"{cell[0]}/{cell[1]} ({passing}/{required} passing audits)")
    if insufficient:
        raise ReleaseEvidenceError(
            "S4 audit sample insufficient: " + "; ".join(insufficient[:10]) +
            (" …" if len(insufficient) > 10 else "")
        )
