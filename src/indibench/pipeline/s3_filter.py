"""S3 — Cross-lab adversarial filter (design §3, D-029/D-035).

Panel: one frontier model each from OpenAI, Anthropic, Google + the best
Indian model (Sarvam-class), answering WITHOUT the source document. An item
survives only if >= FAIL_THRESHOLD of the panel fail it. Exact model
versions are pinned at run time and published with each release.

The survival decision itself is a pure function so it can be unit-tested
and audited independently of any API plumbing.
"""

from dataclasses import dataclass

# D-029: keep iff >=2 of the 4-model panel fail.
PANEL_SIZE = 4
FAIL_THRESHOLD = 2

# D-035: panel model *families*; exact IDs pinned at pipeline-run time.
PANEL_FAMILIES = (
    "openai/gpt-5-class",
    "anthropic/claude-opus-fable-class",
    "google/gemini-pro-class",
    "sarvam/best-available",
)


@dataclass
class PanelResult:
    model_id: str  # pinned version actually used
    answered_correctly: bool
    judged_ambiguous: bool = False  # judge flagged "underspecified"


def survives_filter(results: list[PanelResult]) -> bool:
    """Apply D-029: keep iff >=2 of 4 panel models FAIL the item.

    Ambiguous items are discarded outright (a judge marking the question
    underspecified means difficulty came from bad wording, not knowledge).
    """
    if len(results) != PANEL_SIZE:
        raise ValueError(f"expected {PANEL_SIZE} panel results, got {len(results)}")
    if any(r.judged_ambiguous for r in results):
        return False
    failures = sum(1 for r in results if not r.answered_correctly)
    return failures >= FAIL_THRESHOLD


def run_panel(question: str, answer: str, panel_model_ids: list[str]) -> list[PanelResult]:
    """Query the pinned panel models (WITHOUT the source) and judge each response.

    TODO(build): API calls + dual-judge equivalence check (D-035: one
    Anthropic + one Google judge, third-judge tiebreak). Cost control
    (D-033): call the panel only on candidates that passed a cheap
    pre-screen model.
    """
    raise NotImplementedError("S3 panel plumbing: implementation pending (build phase)")
