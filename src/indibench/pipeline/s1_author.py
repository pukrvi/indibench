"""S1 — Grounded question authoring (design §3, D-009/D-010).

A frontier LLM authors candidate questions GROUNDED in a retrieved chunk of
a source document. The answer key is extracted from the source text with a
quote-level citation — never from the model's parametric memory. Generation
happens natively in the target language/script (no translation step).

The v0-seed candidate pool (D-041) was authored in-session by Claude
(anthropic/claude-fable-5) using this stage's authoring principles but
without a retrieved corpus — those items live in data/candidates/ and carry
grounding_note claims that S2 verifies once API keys are available.
"""

import json

from indibench import providers
from indibench.pipeline.s0_corpus import SourceDocument
from indibench.schema import CandidateDraft

AUTHOR_SYSTEM = """You author frontier-difficulty benchmark questions for IndiBench.
Rules:
- Write in {language} using its native script ({script}); never translate from English.
- The question must be answerable SOLELY from the source excerpt given; take the
  answer key verbatim (or minimally normalized) from the source.
- Prefer hard formats: multi-fact synthesis within the source, assertion-reason,
  sequence ordering, precise statutory/technical detail. No trivia phrasing.
- The question must be self-contained and unambiguous; the answer short.
- Output a JSON array; each element:
  {{"question": str, "answer": str, "answer_type": "exactMatch"|"multipleChoice",
    "choices": [str, ...] | null, "source_quote": str}}"""

AUTHOR_USER = """[source excerpt]
{source_text}

Author up to {n} questions meeting all rules."""


def author_candidates(doc: SourceDocument, n: int, generator_model: str) -> list[CandidateDraft]:
    """Author up to `n` grounded candidates from one document (requires API keys,
    D-042). Cost note (D-033): use the cheapest generator that maintains
    native-script fluency."""
    raw = providers.complete(
        generator_model,
        system=AUTHOR_SYSTEM.format(language=doc.language.name.title(), script=doc.metadata.get("script", "")),
        user=AUTHOR_USER.format(source_text=doc.text, n=n),
        max_tokens=8192,
    )
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"generator returned no JSON array (doc {doc.doc_id})")
    drafts = []
    for entry in json.loads(raw[start : end + 1]):
        drafts.append(
            CandidateDraft(
                question=entry["question"],
                answer=entry["answer"],
                answer_type=entry["answer_type"],
                choices=entry.get("choices"),
                language=doc.language,
                script=doc.metadata.get("script", ""),
                domain=doc.domain,
                generator_model=generator_model,
                grounding_note=f"{doc.source_type}:{doc.doc_id} — {entry.get('source_quote', '')[:200]}",
            )
        )
    return drafts
