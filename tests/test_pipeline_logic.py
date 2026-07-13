"""Unit tests for the pure-logic parts of the pipeline (S3 survival, S4 gates,
S5 split/release, canary)."""

import uuid

from indibench.canary import is_valid_canary, make_canary
from indibench.pipeline.s3_filter import PanelResult, survives_filter
from indibench.pipeline.s4_spotcheck import AuditVerdict, cell_passes, sample_rate_for
from indibench.pipeline.s5_release import split_public_private
from indibench.schema import (
    AnswerType,
    DifficultyEvidence,
    Domain,
    Item,
    Language,
    Provenance,
    Tag,
)


def _panel(fails: int, ambiguous: bool = False) -> list[PanelResult]:
    results = [
        PanelResult(model_id=f"m{i}", answered_correctly=(i >= fails))
        for i in range(4)
    ]
    if ambiguous:
        results[0].judged_ambiguous = True
    return results


def test_filter_keeps_two_or_more_failures():
    assert not survives_filter(_panel(0))
    assert not survives_filter(_panel(1))
    assert survives_filter(_panel(2))
    assert survives_filter(_panel(4))


def test_filter_discards_ambiguous_even_if_hard():
    assert not survives_filter(_panel(4, ambiguous=True))


def _item(tags: list[Tag], language: Language = Language.HINDI) -> Item:
    return Item(
        id=f"ibt-{language.value}-law_constitution-{uuid.uuid4().hex[:8]}",
        question="q",
        answer="a",
        answer_type=AnswerType.EXACT_MATCH,
        language=language,
        script="Deva",
        domain=Domain.LAW_CONSTITUTION,
        tags=tags,
        difficulty_evidence=DifficultyEvidence(
            models_failed=["m1", "m2"], models_passed=["m3", "m4"], filter_round="2026-07"
        ),
        provenance=Provenance(
            source_type="gazette", source_ref="h", generator_model="g", verifier_models=["v"]
        ),
    )


def test_safety_items_always_audited():
    assert sample_rate_for(_item([Tag.SAFETY])) == 1.0
    assert sample_rate_for(_item([])) < 1.0


def test_cell_gate():
    good = [AuditVerdict("i", "e", True, True) for _ in range(20)]
    assert cell_passes(good)
    assert not cell_passes([])  # no audit, no release
    bad = good + [AuditVerdict("j", "e", False, True) for _ in range(2)]
    assert not cell_passes(bad)


def test_split_is_stratified_and_deterministic():
    items = [_item([], Language.HINDI) for _ in range(30)] + [
        _item([], Language.TAMIL) for _ in range(30)
    ]
    pub1, priv1 = split_public_private(items, seed=42)
    # Determinism must hold for the item SET, regardless of input order.
    pub2, priv2 = split_public_private(list(reversed(items)), seed=42)
    assert sorted(i.id for i in pub1) == sorted(i.id for i in pub2)
    assert sorted(i.id for i in priv1) == sorted(i.id for i in priv2)
    assert len(pub1) + len(priv1) == 60
    assert {i.id for i in pub1}.isdisjoint({i.id for i in priv1})
    # Stratified: each language contributes to the private split.
    priv_langs = {i.language for i in priv1}
    assert priv_langs == {Language.HINDI, Language.TAMIL}


def test_mcq_items_validate_choices():
    import pytest

    base = _item([])
    mcq = base.model_copy(
        update={"answer_type": AnswerType.MULTIPLE_CHOICE, "choices": ["x", "y", "z"], "answer": "B"}
    )
    assert Item.model_validate(mcq.model_dump()).answer == "B"
    with pytest.raises(ValueError):
        Item.model_validate(
            base.model_copy(update={"answer_type": AnswerType.MULTIPLE_CHOICE}).model_dump()
        )
    with pytest.raises(ValueError):
        Item.model_validate(
            mcq.model_copy(update={"answer": "D"}).model_dump()  # only A-C valid for 3 choices
        )


def test_canary_roundtrip():
    assert is_valid_canary(make_canary())
    assert not is_valid_canary("not a canary")
