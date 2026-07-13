"""S4 — Human expert spot-check (design §3, D-010/D-033/D-038).

Volunteer domain experts (co-authorship credit, D-033) audit a sample
(default ~10%) per language×domain cell. Safety-tagged items get a
MANDATORY (100%) check (D-038). Cell-level rejection thresholds gate
release: a cell whose audited sample fails too often is regenerated,
not shipped.
"""

from dataclasses import dataclass

from indibench.schema import Item, Tag

DEFAULT_SAMPLE_RATE = 0.10  # D-010 note (tunable)
CELL_REJECTION_THRESHOLD = 0.05  # >5% audited-sample error ⇒ regenerate cell


@dataclass
class AuditVerdict:
    item_id: str
    expert_id: str
    key_correct: bool
    question_well_formed: bool
    notes: str = ""


def sample_rate_for(item: Item) -> float:
    """Safety items are always audited (D-038); everything else is sampled."""
    return 1.0 if Tag.SAFETY in item.tags else DEFAULT_SAMPLE_RATE


def cell_passes(verdicts: list[AuditVerdict]) -> bool:
    """A language×domain cell ships only if its audited error rate is low."""
    if not verdicts:
        return False  # no audit, no release
    errors = sum(1 for v in verdicts if not (v.key_correct and v.question_well_formed))
    return errors / len(verdicts) <= CELL_REJECTION_THRESHOLD
