"""Run the S2→S3 filter over the candidate pool and report yield.

This is THE script to run when API keys are attached. Resumable: every
candidate's outcome is appended to a results JSONL, and already-processed
ids are skipped on re-run (API spend is never repeated).

Real run (requires OPENAI_API_KEY / ANTHROPIC_API_KEY / GOOGLE_API_KEY /
SARVAM_API_KEY in the environment; pin exact model versions here):

    python scripts/run_filter.py \
        --panel openai/<id> anthropic/<id> google/<id> sarvam/<id> \
        --judges anthropic/<id> google/<id> --tiebreak openai/<id>

Dry run without any keys (deterministic mock provider, exercises the entire
plumbing — S2, panel, judging, survival, yield report, promotion):

    python scripts/run_filter.py --mock --skip-s2 --promote-to /tmp/mockrel --version vTEST

After a real run, promote survivors into a versioned release:

    python scripts/run_filter.py ... --promote-to data/releases --version v2026.XX
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from indibench import providers
from indibench.pipeline.promote import promote
from indibench.pipeline.s2_verify import verify_key
from indibench.pipeline.s3_filter import PanelResult, run_panel, survives_filter
from indibench.pipeline.s5_release import split_public_private, write_release
from indibench.schema import CandidateFile

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES_DIR = ROOT / "data" / "candidates" / "v0-seed"
GUID_FILE = ROOT / "data" / "CANARY_GUID"


def _mock_complete(model_id, system, user, max_tokens=4096, temperature=None):
    """Deterministic offline stand-in for providers.complete (--mock).
    Judges vote by content hash; panel models occasionally flag AMBIGUOUS."""
    h = hashlib.sha256(f"{model_id}|{user[:200]}".encode()).digest()[0]
    if "CORRECT or INCORRECT" in system:
        return "CORRECT" if h % 3 == 0 else "INCORRECT"
    if h % 19 == 0:
        return "AMBIGUOUS"
    return "Answer: mock-response"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates-dir", type=Path, default=CANDIDATES_DIR)
    parser.add_argument("--results", type=Path, default=ROOT / "data" / "filter_results.jsonl")
    parser.add_argument("--panel", nargs=4, default=[
        "openai/gpt-5", "anthropic/claude-opus-4-8", "google/gemini-2.5-pro", "sarvam/sarvam-m"])
    parser.add_argument("--judges", nargs=2, default=["anthropic/claude-opus-4-8", "google/gemini-2.5-pro"])
    parser.add_argument("--tiebreak", default="openai/gpt-5")
    parser.add_argument("--skip-s2", action="store_true",
                        help="skip key verification (mock dry runs)")
    parser.add_argument("--mock", action="store_true",
                        help="no API keys needed: deterministic mock provider")
    parser.add_argument("--limit", type=int, default=None, help="max candidates this run")
    parser.add_argument("--promote-to", type=Path, default=None,
                        help="write survivors as a versioned release under this dir")
    parser.add_argument("--version", default=None, help="release version, e.g. v2026.07")
    args = parser.parse_args()

    if args.mock:
        providers.complete = _mock_complete
        print("MOCK MODE — deterministic offline provider; results are plumbing-only")

    done: dict[str, dict] = {}
    if args.results.exists():
        for line in args.results.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                done[record["id"]] = record

    drafts = []
    for path in sorted(args.candidates_dir.glob("*.json")):
        drafts.extend(CandidateFile.model_validate_json(path.read_text(encoding="utf-8")).examples)
    todo = [d for d in drafts if d.id not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{len(drafts)} candidates, {len(done)} already processed, running {len(todo)}")

    with args.results.open("a", encoding="utf-8") as out:
        for n, draft in enumerate(todo, 1):
            record = {"id": draft.id, "language": draft.language.value,
                      "domain": draft.domain.value}
            try:
                if args.skip_s2:
                    record["s2_ok"] = None
                else:
                    record["s2_ok"] = verify_key(
                        draft.question, draft.answer, draft.grounding_note,
                        verifier_models=list(args.judges), judge_models=tuple(args.judges),
                        tiebreak_model=args.tiebreak, choices=draft.choices)
                if record.get("s2_ok") is False:
                    record["survived"] = False
                    record["panel"] = []
                else:
                    results = run_panel(
                        draft.question, draft.answer, list(args.panel),
                        judge_models=tuple(args.judges), tiebreak_model=args.tiebreak,
                        choices=draft.choices)
                    record["panel"] = [
                        {"model": r.model_id, "correct": r.answered_correctly,
                         "ambiguous": r.judged_ambiguous} for r in results]
                    record["survived"] = survives_filter(results)
            except Exception as exc:
                record["error"] = str(exc)
                record["survived"] = False
            done[draft.id] = record
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            if n % 20 == 0:
                print(f"  {n}/{len(todo)} processed")

    survivors = {i for i, r in done.items() if r.get("survived")}
    by_lang = Counter(r["language"] for r in done.values() if r.get("survived"))
    print(f"\nYield report: {len(survivors)}/{len(done)} survived "
          f"({100 * len(survivors) / max(len(done), 1):.0f}%)")
    for lang, count in sorted(by_lang.items()):
        print(f"  {lang}: {count}")
    failed_s2 = sum(1 for r in done.values() if r.get("s2_ok") is False)
    errored = sum(1 for r in done.values() if "error" in r)
    print(f"s2-failed: {failed_s2} · errored: {errored}")

    if args.promote_to and args.version:
        filter_round = args.version
        items = []
        for draft in drafts:
            record = done.get(draft.id)
            if not record or not record.get("survived") or not record.get("panel"):
                continue
            results = [PanelResult(model_id=p["model"], answered_correctly=p["correct"],
                                   judged_ambiguous=p["ambiguous"]) for p in record["panel"]]
            items.append(promote(draft, results, filter_round, verifier_models=list(args.judges)))
        public, private = split_public_private(items, seed=2026)
        written = write_release(public, args.promote_to / "public", args.version,
                                GUID_FILE.read_text().strip())
        write_release(private, args.promote_to / "private", args.version,
                      GUID_FILE.read_text().strip())
        print(f"promoted {len(items)} survivors → {len(public)} public / {len(private)} private "
              f"({len(written)} public files under {args.promote_to}/public/{args.version})")
        print("REMINDER: the private split must NEVER be committed or published (D-032)")


if __name__ == "__main__":
    main()
