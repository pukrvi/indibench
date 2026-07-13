"""S2 — Answer-key verification (design §3; exists because of HLE's key-error audit).

An independent model panel re-derives the answer FROM THE SOURCE CHUNK.
Disagreement with the authored key ⇒ discard (or route to the human queue).
This guards against generator hallucination before any expensive S3 calls.

For v0-seed candidates (D-041) the "source chunk" is the item's
grounding_note claim — S2 verifiers are additionally asked to CONFIRM the
claimed source exists and supports the key, which makes this stage the
safety net for in-session authoring until the S0 corpus lands.
"""

from indibench import providers
from indibench.judging import judge_equivalent

VERIFY_SYSTEM = (
    "You verify benchmark answer keys. Using ONLY the source material given, "
    "derive the answer to the question. Reply in this exact format:\n"
    "Answer: {your succinct final answer}\n"
    "If the source does not contain enough information to answer, reply "
    "exactly: INSUFFICIENT"
)

VERIFY_USER = """[source]
{source}

[question]
{question}"""


def verify_key(
    question: str,
    answer: str,
    source_text: str,
    verifier_models: list[str],
    judge_models: tuple[str, str],
    tiebreak_model: str,
    choices: list[str] | None = None,
) -> bool:
    """True iff EVERY verifier independently derives an answer equivalent to
    the key from the source. INSUFFICIENT from any verifier fails the item
    (route to the human queue rather than silently passing). MCQ items render
    their choices into the prompt and judge against letter + choice text."""
    from indibench.judging import mcq_reference, render_mcq

    rendered = render_mcq(question, choices)
    reference = mcq_reference(answer, choices)
    for model_id in verifier_models:
        raw = providers.complete(
            model_id,
            system=VERIFY_SYSTEM,
            user=VERIFY_USER.format(source=source_text, question=rendered),
            max_tokens=1024,
        )
        if raw.strip().upper().startswith("INSUFFICIENT"):
            return False
        derived = raw.split("Answer:", 1)[-1].strip() if "Answer:" in raw else raw.strip()
        if not judge_equivalent(rendered, derived, reference, judge_models, tiebreak_model):
            return False
    return True
