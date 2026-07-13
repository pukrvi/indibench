"""S2 — Answer-key verification (design §3; exists because of HLE's key-error audit).

An independent model panel re-derives the answer FROM THE SOURCE CHUNK.
Disagreement with the authored key ⇒ discard (or route to the human queue).
This guards against generator hallucination before any expensive S3 calls.
"""

from indibench.pipeline.s1_author import CandidateItem


def verify_key(
    candidate: CandidateItem, source_text: str, verifier_models: list[str]
) -> bool:
    """True iff every verifier independently derives the same key from the source.

    TODO(build): per-verifier API call with the source chunk + question
    (answer withheld), equivalence check via string/numeric normalization,
    escalate near-misses to the human queue rather than silently passing.
    """
    raise NotImplementedError("S2 verification: implementation pending (build phase)")
