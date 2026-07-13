# S0 source manifests

This directory will hold **private, license-reviewed source manifests** used
to ground IndiBench questions. It intentionally contains no source text and
no manifest yet: the current `v0-seed` is a review candidate pool, not a
source-grounded dataset.

## Manifest format

One JSON object per line (`.jsonl`), validated by
`indibench.pipeline.s0_corpus.load_source_manifest`:

```json
{
  "doc_id": "hi-law-constitution-001",
  "language": "hi",
  "domain": "law_constitution",
  "source_type": "gazette",
  "license": "GODL-India",
  "provenance_url": "https://example.gov.in/document",
  "content_sha256": "<64 lowercase hex characters>",
  "metadata": {"title": "...", "retrieved_at": "2026-07-13"}
}
```

Allowed licenses are deliberately narrow: `GODL-India`, `public-record`,
`CC-BY-4.0`, or `CC-BY-SA-4.0`. Every candidate that may ship must carry a
matching `source_document_id`; its language and domain must match the
registered source.

Do not add copyrighted source text to this repository. Store it in the
private corpus workspace and record only its SHA-256 digest here.
