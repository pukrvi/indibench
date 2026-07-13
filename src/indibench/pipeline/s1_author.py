"""S1 — Grounded question authoring (design §3, D-009/D-010).

A frontier LLM authors candidate questions GROUNDED in a retrieved chunk of
a source document. The answer key is extracted from the source text with a
quote-level citation — never from the model's parametric memory. Generation
happens natively in the target language/script (no translation step).
"""

from dataclasses import dataclass

from indibench.pipeline.s0_corpus import SourceDocument
from indibench.schema import AnswerType


@dataclass
class CandidateItem:
    """Pre-filter candidate; becomes schema.Item only if it survives S2–S4."""

    question: str
    answer: str
    answer_type: AnswerType
    choices: list[str] | None
    source_doc_id: str
    source_quote: str  # the exact source span the key derives from
    generator_model: str


def author_candidates(
    doc: SourceDocument, n: int, generator_model: str
) -> list[CandidateItem]:
    """Author up to `n` grounded candidates from one document.

    TODO(build): prompt template (hard question formats per audit: assertion-
    reason, matching, sequencing, multi-hop within the document), API call,
    structured-output parse into CandidateItem. Cost note (D-033): use the
    cheapest generator that maintains native-script fluency.
    """
    raise NotImplementedError("S1 authoring: implementation pending (build phase)")
