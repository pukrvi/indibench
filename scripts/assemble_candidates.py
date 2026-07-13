"""Assemble authored candidate drafts into canary-wrapped candidate files.

Reads data/candidates/authoring/*.jsonl (one CandidateDraft-shaped JSON per
line), validates every line against the schema, assigns stable candidate ids,
and writes one canary-wrapped file per language track to
data/candidates/v0-seed/.

    python scripts/assemble_candidates.py [--generator anthropic/claude-fable-5]

Deterministic: ids derive from a content hash, so re-running never reshuffles
identity. Refuses to write if any line fails validation.
"""

import argparse
import hashlib
import json
from pathlib import Path

from indibench.canary import make_canary
from indibench.schema import CandidateDraft, CandidateFile

ROOT = Path(__file__).resolve().parent.parent
AUTHORING_DIR = ROOT / "data" / "candidates" / "authoring"
OUT_DIR = ROOT / "data" / "candidates" / "v0-seed"
GUID_FILE = ROOT / "data" / "CANARY_GUID"


def content_id(draft: CandidateDraft) -> str:
    digest = hashlib.sha256(
        f"{draft.language.value}|{draft.domain.value}|{draft.question}".encode()
    ).hexdigest()[:8]
    return f"ibc-{draft.language.value}-{draft.domain.value}-{digest}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", default="anthropic/claude-fable-5")
    args = parser.parse_args()

    canary = make_canary(GUID_FILE.read_text().strip())
    drafts: list[CandidateDraft] = []
    errors: list[str] = []
    for path in sorted(AUTHORING_DIR.glob("*.jsonl")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                data.setdefault("generator_model", args.generator)
                draft = CandidateDraft.model_validate(data)
                draft.id = content_id(draft)
                drafts.append(draft)
            except Exception as exc:
                errors.append(f"{path.name}:{lineno}: {exc}")
    if errors:
        raise SystemExit("validation failed:\n" + "\n".join(errors))

    ids = [d.id for d in drafts]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise SystemExit(f"duplicate candidate ids (identical questions?): {sorted(dupes)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_lang: dict[str, list[CandidateDraft]] = {}
    for draft in drafts:
        by_lang.setdefault(draft.language.value, []).append(draft)
    for lang, lang_drafts in sorted(by_lang.items()):
        payload = CandidateFile(canary=canary, examples=lang_drafts)
        out = OUT_DIR / f"indibench_text_candidates_{lang}.json"
        out.write_text(payload.model_dump_json(indent=1), encoding="utf-8")
        print(f"{out.relative_to(ROOT)}: {len(lang_drafts)} candidates")
    print(f"total: {len(drafts)} candidates across {len(by_lang)} language codes")


if __name__ == "__main__":
    main()
