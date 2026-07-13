"""S3 — Cross-lab adversarial filter (design §3, D-029/D-035).

Panel: one frontier model each from OpenAI, Anthropic, Google + the best
Indian model (Sarvam-class), answering WITHOUT the source document. An item
survives only if >= FAIL_THRESHOLD of the panel fail it. Exact model
versions are pinned at run time and published with each release.

The survival decision itself is a pure function so it can be unit-tested
and audited independently of any API plumbing.
"""

from dataclasses import dataclass

from indibench import providers
from indibench.judging import judge_equivalent

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

PANEL_SYSTEM = (
    "Answer the question. Reply in the same language as the question, in this "
    "exact format:\n"
    "Answer: {your succinct final answer}\n"
    "If the question is ambiguous or underspecified, reply exactly: AMBIGUOUS"
)


@dataclass
class PanelResult:
    model_id: str  # pinned version actually used
    answered_correctly: bool
    judged_ambiguous: bool = False  # model flagged "underspecified"


def survives_filter(results: list[PanelResult]) -> bool:
    """Apply D-029: keep iff >=2 of 4 panel models FAIL the item.

    Ambiguous items are discarded outright (a model marking the question
    underspecified means difficulty came from bad wording, not knowledge).
    """
    if len(results) != PANEL_SIZE:
        raise ValueError(f"expected {PANEL_SIZE} panel results, got {len(results)}")
    if any(r.judged_ambiguous for r in results):
        return False
    failures = sum(1 for r in results if not r.answered_correctly)
    return failures >= FAIL_THRESHOLD


def run_panel(
    question: str,
    answer: str,
    panel_model_ids: list[str],
    judge_models: tuple[str, str],
    tiebreak_model: str,
) -> list[PanelResult]:
    """Query the pinned panel models (WITHOUT the source) and judge each response.

    Requires provider API keys in the environment (D-042). Cost control
    (D-033): callers should pre-screen candidates with a cheap model before
    invoking the full panel.
    """
    results: list[PanelResult] = []
    for model_id in panel_model_ids:
        raw = providers.complete(model_id, system=PANEL_SYSTEM, user=question, max_tokens=1024)
        if "AMBIGUOUS" in raw.upper():
            results.append(PanelResult(model_id=model_id, answered_correctly=False,
                                       judged_ambiguous=True))
            continue
        response = raw.split("Answer:", 1)[-1].strip() if "Answer:" in raw else raw.strip()
        correct = judge_equivalent(question, response, answer, judge_models, tiebreak_model)
        results.append(PanelResult(model_id=model_id, answered_correctly=correct))
    return results
