"""S0 — Grounding-corpus registration (D-010/D-017).

Researchers discover source documents outside this library, review their
licensing, and register immutable metadata in a JSONL manifest.  This module
deliberately never crawls external sites automatically: a benchmark must not
silently ingest material whose use rights have not been checked.
"""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from indibench.schema import Domain, Language


class SourceDocument(BaseModel):
    """A license-reviewed S0 grounding source.

    Source text stays in the private corpus workspace. The manifest keeps
    immutable metadata and its content hash without redistributing text.
    """

    doc_id: str
    language: Language
    domain: Domain
    source_type: str  # textbook | gazette | case_law | syllabus | manual
    license: Literal["GODL-India", "public-record", "CC-BY-4.0", "CC-BY-SA-4.0"]
    provenance_url: HttpUrl
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    metadata: dict = Field(default_factory=dict)


def source_content_hash(text: str) -> str:
    """Hash private source content for the manifest."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_source_manifest(path: Path) -> dict[str, SourceDocument]:
    """Load a JSONL S0 manifest and reject duplicate identifiers."""
    records: dict[str, SourceDocument] = {}
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        source = SourceDocument.model_validate(json.loads(line))
        if source.doc_id in records:
            raise ValueError(f"{path}:{lineno}: duplicate source doc_id {source.doc_id!r}")
        records[source.doc_id] = source
    if not records:
        raise ValueError(f"{path}: source manifest is empty")
    return records


def curate_cell(language: Language, domain: Domain) -> list[SourceDocument]:
    """Deliberately refuses implicit discovery.

    Register license-reviewed sources in a manifest with
    :func:`load_source_manifest`; source discovery is a human/LLM research
    workflow, not an unattended scraper.
    """
    raise RuntimeError(
        "S0 discovery is not automated. Register license-reviewed sources in a "
        "manifest, then use load_source_manifest()."
    )
