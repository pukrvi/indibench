"""Answer-equivalence judging shared by S2/S3 and offline grading (D-035).

Dual-judge protocol: one Anthropic + one Google judge; disagreement goes to a
third judge (tiebreak). Judges see question, model answer, and the key —
never which model produced the answer.
"""

import re

from indibench import providers

JUDGE_SYSTEM = (
    "You judge whether a response's final answer is equivalent to a reference "
    "answer. Allow small numerical tolerance and treat transliteration variants "
    "of the same Indian-language term as equivalent. Reply with exactly one "
    "word: CORRECT or INCORRECT."
)

JUDGE_USER = """[question]
{question}

[response]
{response}

[reference_answer]
{reference}"""


def normalize(text: str) -> str:
    """Cheap pre-judge normalization: casefold, strip punctuation/whitespace."""
    return re.sub(r"[\s\.,;:!?'\"()\-–—]+", "", text).casefold()


def render_mcq(question: str, choices: list[str] | None) -> str:
    """Render lettered choices into the question text (A-H). No-op without choices."""
    if not choices:
        return question
    letters = "ABCDEFGH"
    rendered = "\n".join(f"{letters[i]}. {c}" for i, c in enumerate(choices))
    return f"{question}\n\n{rendered}"


def mcq_reference(answer: str, choices: list[str] | None) -> str:
    """Judge-facing reference for MCQ items: letter AND choice text, so a
    free-text response matching either form grades correctly."""
    if not choices:
        return answer
    idx = ord(answer) - ord("A")
    return f"{answer} ({choices[idx]})"


def judge_equivalent(
    question: str,
    response: str,
    reference: str,
    judge_models: tuple[str, str],
    tiebreak_model: str,
) -> bool:
    """Dual-judge with third-judge tiebreak (D-035). Exact-normalized matches
    short-circuit without any API call (cost control, D-033); empty
    normalizations never short-circuit."""
    if normalize(response) and normalize(response) == normalize(reference):
        return True
    votes = [_one_judge(m, question, response, reference) for m in judge_models]
    if votes[0] == votes[1]:
        return votes[0]
    return _one_judge(tiebreak_model, question, response, reference)


def _one_judge(model_id: str, question: str, response: str, reference: str) -> bool:
    verdict = providers.complete(
        model_id,
        system=JUDGE_SYSTEM,
        user=JUDGE_USER.format(question=question, response=response, reference=reference),
        max_tokens=64,  # headroom for reasoning-model judges; instruction is one word
    )
    return "CORRECT" in verdict.upper() and "INCORRECT" not in verdict.upper()
