# Runbook — Running the IndiBench Pipeline

Last updated: 2026-07-13, after the pre-keys readiness audit.

## Readiness status (verified WITHOUT API keys)

| Check | Result |
|---|---|
| Unit + integration tests | ✅ 14 passing (`pytest tests/`) |
| All 240 v0-seed candidates schema-valid, canary-wrapped, unfiltered-labeled | ✅ (`scripts/assemble_candidates.py` re-validates) |
| Full offline dry-run of the filter orchestration (`--mock`) over all 240 items: S3 panel → judging → survival rule → yield report → promotion → public/private split → test-only versioned files | ✅ |
| Resumability (re-run skips processed ids; no double API spend) | ✅ tested |
| Inspect AI harness end-to-end (loader + canary check + generation + model-graded scoring) with scripted mock model: GRADE: C → 1.0, GRADE: I → 0.0 | ✅ |
| Standalone `predict.py` / `judge.py` CLI smoke + calibration math unit-tested (full CLI flows need a live endpoint) | ✅ |
| Providers fail loudly and helpfully without keys (key check before SDK import) | ✅ tested |
| Keys-day guardrails: errored candidates retry by default, consecutive-error abort, corrupt-tail tolerance, partial-promotion refusal, run-config sidecar mismatch check | ✅ tested |
| Lint (ruff) | ✅ clean |

Known limits before keys: S2/S3 quality outcomes are unmeasurable offline (mock
yield numbers are plumbing checks, not difficulty data), and Indic-script
`review_priority: high` items still await native-speaker review (S4).

**Release gate:** the v0 seed has claimed grounding notes but no S0 source
manifest or S4 expert verdicts. It can be filtered with keys but cannot become
an official release. A real promotion requires both `--sources` (license-
reviewed S0 JSONL) and `--audit-verdicts` (S4 JSONL). See
[`data/sources/README.md`](../data/sources/README.md) and the
[implementation audit](research/2026-07-13-implementation-audit.md).

## When API keys arrive

1. Export keys (any subset works; the panel needs all four):
   `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
   `SARVAM_API_KEY` (+ `SARVAM_BASE_URL` for Sarvam's OpenAI-compatible endpoint).
2. Install pipeline extras: `pip install -e ".[pipeline]"`.
3. **Pin exact model versions** (D-035) and do a tiny smoke run first:

   ```bash
   python scripts/run_filter.py \
     --panel openai/<pinned> anthropic/<pinned> google/<pinned> sarvam/<pinned> \
     --judges anthropic/<pinned> google/<pinned> --tiebreak openai/<pinned> \
     --limit 10
   ```

4. Inspect the yield report + `data/filter_results.jsonl`; then drop `--limit`
   for the full 240. Re-runs resume automatically.
5. **Before promotion**, register the verified sources and collect S4 expert
   verdicts. Promote survivors only with:
   `--promote-to data/releases --version v2026.XX --sources data/sources/<manifest>.jsonl --audit-verdicts <audits>.jsonl`
   (all flags required; refuses if candidates remain unprocessed unless
   `--force-partial-promotion`).
   The `private/` output directory must NEVER be committed (D-032) — verify
   the `data/releases/private/` entry still exists in `.gitignore`.
6. Record the pinned model IDs + yield stats in `docs/DECISIONS.md`. The
   results file's `.meta.json` sidecar pins the run config; changing model
   pins requires a fresh `--results` path.

Operational notes: errored candidates (rate limits, bad pins) are retried
automatically on re-run; the run aborts after 5 consecutive errors. The
standalone `judge.py` reaches non-OpenAI judges via `--base-url` pointing at
an OpenAI-compatible gateway; the Inspect harness needs no gateway
(`--model` handles all providers natively).

## Evaluating a model

- **One-command runner (recommended):** `python scripts/run_benchmark.py --model <id> --judge <id> [--base-url <local>] [--input-cost X --output-cost Y]`
  → writes `results/<run-name>/` with `results.csv` (per-item correctness,
  TTFT, tokens/sec, tokens, cost), `summary.csv`/`summary.json`, and a visual
  `overview.html`. `--mock` dry-runs the whole thing offline. Full
  instructions in the README's "Run the benchmark" section.
- Inspect AI: `inspect eval evals/inspect/indibench_text.py -T data_file=<release file> --model <model>`
- Standalone: `python evals/standalone/predict.py --data <file> --model <id> [--base-url <local>]`
  then `python evals/standalone/judge.py --data <file> --predictions <out> --judge <id>`
  (official runs: once per judge — Anthropic + Google — per D-035).
