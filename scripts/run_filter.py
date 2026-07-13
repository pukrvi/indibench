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
from indibench.pipeline.release_gate import load_audit_verdicts, require_release_evidence
from indibench.pipeline.s0_corpus import load_source_manifest
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
    parser.add_argument("--no-retry-errors", action="store_true",
                        help="do NOT re-attempt candidates whose previous run errored")
    parser.add_argument("--max-consecutive-errors", type=int, default=5,
                        help="abort the run after this many errors in a row (bad key/model id)")
    parser.add_argument("--promote-to", type=Path, default=None,
                        help="write survivors as a versioned release under this dir")
    parser.add_argument("--version", default=None, help="release version, e.g. v2026.07")
    parser.add_argument("--sources", type=Path, default=None,
                        help="license-reviewed S0 source manifest JSONL (required for real release)")
    parser.add_argument("--audit-verdicts", type=Path, default=None,
                        help="S4 human-audit verdicts JSONL (required for real release)")
    parser.add_argument("--allow-mock-release", action="store_true",
                        help="TEST ONLY: permit --mock to write synthetic release files")
    parser.add_argument("--force-partial-promotion", action="store_true",
                        help="allow promotion even if not every candidate has been processed")
    args = parser.parse_args()

    if bool(args.promote_to) != bool(args.version):
        parser.error("--promote-to and --version must be used together")
    if args.allow_mock_release and not args.mock:
        parser.error("--allow-mock-release is valid only with --mock")
    if args.promote_to and args.mock and not args.allow_mock_release:
        parser.error("--mock cannot write a release without --allow-mock-release (test only)")

    if args.mock:
        providers.complete = _mock_complete
        print("MOCK MODE — deterministic offline provider; results are plumbing-only")

    # Config sidecar: refuse to silently mix records produced under different
    # panel/judge pins in one results file.
    run_config = {"panel": list(args.panel), "judges": list(args.judges),
                  "tiebreak": args.tiebreak, "mock": args.mock}
    meta_path = args.results.with_suffix(".meta.json")
    if meta_path.exists():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        if previous != run_config:
            parser.error(
                f"model pins differ from the existing results file's run config "
                f"({meta_path}). Use a fresh --results path for a new configuration.")
    else:
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(run_config, indent=1), encoding="utf-8")

    done: dict[str, dict] = {}
    if args.results.exists():
        lines = args.results.read_text(encoding="utf-8").splitlines()
        good_lines = []
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if lineno == len(lines):
                    print(f"warning: dropping truncated final line in {args.results} "
                          f"(interrupted previous run)")
                    continue
                raise SystemExit(f"{args.results}:{lineno}: corrupt (non-final) line — "
                                 f"inspect the file manually")
            done[record["id"]] = record
            good_lines.append(line)
        # rewrite without the truncated tail so append stays clean
        if len(good_lines) != len([line for line in lines if line.strip()]):
            args.results.write_text("\n".join(good_lines) + "\n", encoding="utf-8")

    # Errored records are retried by default — a bad key or rate-limit burst
    # must never permanently mark candidates as processed (readiness-audit finding).
    retryable = {i for i, r in done.items() if "error" in r and not args.no_retry_errors}
    for item_id in retryable:
        del done[item_id]

    drafts = []
    for path in sorted(args.candidates_dir.glob("*.json")):
        drafts.extend(CandidateFile.model_validate_json(path.read_text(encoding="utf-8")).examples)
    todo = [d for d in drafts if d.id not in done]
    if args.limit is not None:
        todo = todo[: args.limit]
    print(f"{len(drafts)} candidates, {len(done)} already processed"
          f"{f' ({len(retryable)} errored queued for retry)' if retryable else ''}, "
          f"running {len(todo)}")

    consecutive_errors = 0
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
                consecutive_errors += 1
            else:
                consecutive_errors = 0
            done[draft.id] = record
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            out.flush()
            if consecutive_errors >= args.max_consecutive_errors:
                print(f"ABORTING: {consecutive_errors} consecutive errors "
                      f"(last: {record['error']}) — check keys/model ids, then re-run "
                      f"(errored candidates retry automatically)")
                break
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
        if args.skip_s2 and not args.mock:
            raise SystemExit("REFUSING to promote: real releases require S2 verification")
        unprocessed = len(drafts) - len(done)
        if unprocessed > 0 and not args.force_partial_promotion:
            raise SystemExit(
                f"REFUSING to promote: {unprocessed}/{len(drafts)} candidates were never "
                f"processed. Finish the run, or pass --force-partial-promotion.")
        surviving_drafts = [
            draft for draft in drafts
            if (record := done.get(draft.id)) and record.get("survived") and record.get("panel")
        ]
        sources = None
        if not args.mock:
            if not args.sources or not args.audit_verdicts:
                raise SystemExit(
                    "REFUSING to promote: real releases require --sources (S0 manifest) "
                    "and --audit-verdicts (S4 evidence)"
                )
            sources = load_source_manifest(args.sources)
            require_release_evidence(surviving_drafts, sources, load_audit_verdicts(args.audit_verdicts))

        filter_round = args.version
        items = []
        for draft in surviving_drafts:
            record = done.get(draft.id)
            results = [PanelResult(model_id=p["model"], answered_correctly=p["correct"],
                                   judged_ambiguous=p["ambiguous"]) for p in record["panel"]]
            if args.mock:
                # Mock releases only exercise S5 in tests and are never official.
                from indibench.pipeline.s0_corpus import SourceDocument
                source = SourceDocument(
                    doc_id=draft.source_document_id or f"mock-{draft.id}",
                    language=draft.language, domain=draft.domain, source_type="test-fixture",
                    license="CC-BY-4.0", provenance_url="https://example.invalid/",
                    content_sha256="0" * 64,
                )
                draft.source_document_id = source.doc_id
            else:
                source = sources[draft.source_document_id]  # validated above
            items.append(promote(draft, results, filter_round,
                                 verifier_models=list(args.judges), source=source))
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
