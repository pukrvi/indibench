"""S0 — Grounding-corpus curation (design §3, D-017).

Collects hard Indian source documents per language×domain cell: regional-
language textbooks, state gazettes, case law, government manuals; exam
SYLLABI as grounding only — never harvested exam questions (D-017).

Source-licensing policy (proposed default recorded in D-039/D-040 note):
prefer government/public-domain material (GODL-India, court judgments as
public record); tag every document with license + provenance; never
reproduce long excerpts inside generated questions.
"""

from dataclasses import dataclass, field

from indibench.schema import Domain, Language


@dataclass
class SourceDocument:
    doc_id: str
    language: Language
    domain: Domain
    source_type: str  # textbook | gazette | case_law | syllabus | manual
    license: str  # e.g. "GODL-India", "public-record", "CC-BY-4.0"
    provenance_url: str
    text: str
    metadata: dict = field(default_factory=dict)


def curate_cell(language: Language, domain: Domain) -> list[SourceDocument]:
    """Collect candidate grounding documents for one language×domain cell.

    TODO(build): LLM-assisted discovery over public repositories (state
    education portals, gazette archives, Indian Kanoon, indicnlp_catalog
    leads) followed by license verification. Returns only documents whose
    license tag passes the policy above.
    """
    raise NotImplementedError("S0 corpus curation: implementation pending (build phase)")
