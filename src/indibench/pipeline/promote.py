"""Promote surviving candidates into release Items (bridges S3 → S5).

A CandidateDraft that passed S2 verification and the S3 adversarial filter
becomes a schema.Item: difficulty_evidence is attached from the panel
results, and provenance is coarsened for public release (the full
grounding_note stays in private pipeline records; only a hash ships).
"""

from indibench.pipeline.s0_corpus import SourceDocument
from indibench.pipeline.s3_filter import PanelResult, survives_filter
from indibench.schema import CandidateDraft, DifficultyEvidence, Item, Provenance


def promote(
    draft: CandidateDraft,
    results: list[PanelResult],
    filter_round: str,
    verifier_models: list[str],
    source: SourceDocument,
) -> Item:
    """Convert a surviving draft to a release Item. Raises if the draft did
    not survive, has no assembly id, or lacks a matching registered S0 source."""
    if not draft.id:
        raise ValueError("draft has no id — run scripts/assemble_candidates.py first")
    if not draft.id.startswith("ibc-"):
        raise ValueError(f"unexpected candidate id prefix: {draft.id}")
    if draft.source_document_id != source.doc_id:
        raise ValueError(f"{draft.id} is not linked to source {source.doc_id}")
    if source.language != draft.language or source.domain != draft.domain:
        raise ValueError(f"{draft.id} source language/domain does not match candidate")
    if not survives_filter(results):
        raise ValueError(f"{draft.id} did not survive the filter — cannot promote")
    return Item(
        id="ibt-" + draft.id.removeprefix("ibc-"),
        question=draft.question,
        answer=draft.answer,
        answer_type=draft.answer_type,
        choices=draft.choices,
        language=draft.language,
        script=draft.script,
        domain=draft.domain,
        tags=draft.tags,
        difficulty_evidence=DifficultyEvidence(
            models_failed=[r.model_id for r in results if not r.answered_correctly],
            models_passed=[r.model_id for r in results if r.answered_correctly],
            filter_round=filter_round,
        ),
        provenance=Provenance(
            source_type=source.source_type,
            source_ref=source.content_sha256[:12],
            generator_model=draft.generator_model,
            verifier_models=verifier_models,
        ),
    )
