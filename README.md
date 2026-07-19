# IndiBench

**Aiming to be the only benchmark you need to evaluate AI, LLMs, and Agents on
Indian Languages and Tasks** — open, lab-neutral, and frontier-hard, across
text, speech, vision, and agentic use cases.

> Today's best models should score *low* on IndiBench. That's the point.

[![Code License: MIT](https://img.shields.io/badge/code-MIT-green.svg)](LICENSE)
[![Data License: CC BY 4.0](https://img.shields.io/badge/data-CC%20BY%204.0-blue.svg)](https://creativecommons.org/licenses/by/4.0/)
![Status](https://img.shields.io/badge/status-building%20Phase%201-orange)

## The idea

Frontier AI has a benchmark suite it respects — Humanity's Last Exam for
expert knowledge, SWE-bench for software engineering. **India has nothing in
that suite.** Every open Indian benchmark is either saturated (frontier models
score 56–77%), harvested from public exams (contaminated by construction),
translated from Western tests (measures translationese, not India), or closed
(you can't run it, audit it, or build on it).

IndiBench adds India to the frontier suite: benchmarks hard enough that
today's best models fail them, in Indian languages, on Indian use cases,
fully open — data, harness, and the pipeline that generates it.

### The thesis: India is a multimodal evaluation problem

Text-only evaluation structurally under-measures what matters in India
(see [docs/THESIS.md](docs/THESIS.md)):

- **Voice is the primary interface** for hundreds of millions of Indian
  users — and ASR still runs 20–30% WER on Indian languages. Both directions
  (speech-to-text AND text-to-speech / spoken interaction) need frontier
  evaluation.
- **Vision models fail Indian culture** — and image generators misrepresent
  it. Understanding India in images AND producing historically, contextually
  accurate images of India are both core capabilities, and nothing measures
  them systematically.
- **Language understanding** must be native-script and code-mixed
  (Hinglish/Tanglish) at frontier difficulty — not translated.
- **Historical accuracy** is a scored dimension throughout.

### Four phases

| Phase | Benchmark | What it evaluates |
|---|---|---|
| 1 | **IndiBench-Text** *(building now)* | Frontier-difficulty knowledge & reasoning: 12 language tracks (Hindi, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia, English-about-India, code-mixed Hinglish/Tanglish), 10 balanced domains from law and governance to agriculture and regional literature, plus a tagged safety slice |
| 2 | **IndiBench-Speech** | STT *and* TTS/spoken interaction, dialect and acoustic diversity |
| 3 | **IndiBench-Vision** | Understanding India in images *and* culturally/historically accurate image generation |
| 4 | **IndiBench-Agent** | Agents on Indian rails: UPI, IRCTC, government-portal style simulated domains with deterministic verification |

## How it stays hard and trustworthy

The pipeline is the product ([design doc](docs/design/phase1-indibench-text.md)):

```
S0 Corpus     → hard Indian source documents (regional-language textbooks,
                state gazettes, case law; exam syllabi as grounding only)
S1 Authoring  → frontier LLMs write questions GROUNDED in those documents;
                answer keys come from the source, never model memory
S2 Verify     → an independent model panel re-derives every key from the source
S3 Filter     → cross-lab adversarial panel (OpenAI, Anthropic, Google + best
                Indian model) answers WITHOUT the source; an item survives only
                if ≥2 of 4 models fail it
S4 Spot-check → domain experts audit samples (safety items: 100%)
S5 Release    → canary GUID in every file, ~500-question private held-out
                split, date-stamped versions
```

- **Contamination defense:** canary strings + private split + the benchmark
  is *renewable* — the pipeline reruns every 6 months, replacing ~1/3 of items.
- **Lab-neutral:** adversarially filtered against all frontier labs' models,
  not one lab's; dual LLM-judges from two different labs with published
  agreement stats; maintainer-run leaderboard with raw logs published.
- **Runs anywhere:** [Inspect AI](https://inspect.aisi.org.uk/) task +
  HLE-style standalone scripts that run locally on Ubuntu.

## Status

**Alignment phase complete — build phase started (July 2026).**
Scope was locked through a recorded, question-by-question alignment loop:
every decision is in [docs/DECISIONS.md](docs/DECISIONS.md) (40 decisions and
counting), every owner input in
[docs/USER_INPUTS.md](docs/USER_INPUTS.md), and the audit of 20 existing
Indian/frontier benchmarks that shaped the design is in
[docs/research/2026-07-13-benchmark-audit.md](docs/research/2026-07-13-benchmark-audit.md).

No dataset has been released yet. The repository currently contains a
**240-item unfiltered pilot seed**, not a benchmark release: it must first be
linked to license-reviewed source records, pass S2/S3, and receive S4 expert
audits. Phase 1 v1 target: ~2,500 adversarially filtered questions +
leaderboard + paper + inspect_evals registration. See the
[implementation audit](docs/research/2026-07-13-implementation-audit.md).

## Run the benchmark

Evaluate any model on the current pool and get a results folder with per-item
CSV data plus a visual overview (accuracy, time-to-first-token, tokens/sec,
tokens generated, total cost).

### 1. Setup

```bash
git clone https://github.com/pukrvi/indibench
cd indibench
python3 -m venv .venv && source .venv/bin/activate   # Python 3.10+
pip install -e ".[eval]"
pytest tests/ -q        # optional sanity check — all tests run offline
```

### 2. Try it with zero keys (offline dry run)

```bash
python scripts/run_benchmark.py --mock
```

This runs a deterministic fake model over all 240 items and produces a real
results folder — use it to see exactly what you'll get before spending money.

### 3. Run a real model

Any OpenAI-compatible endpoint works. Pricing flags are USD per **million**
tokens (from your provider's pricing page); omit them and cost reports 0.

```bash
export OPENAI_API_KEY=sk-...
python scripts/run_benchmark.py \
    --model gpt-5-mini \
    --judge gpt-5-mini \
    --input-cost 0.25 --output-cost 2.00
```

Local model (Ollama / vLLM — no key needed):

```bash
python scripts/run_benchmark.py --model llama3 --base-url http://localhost:11434/v1
```

Pass `--effort <level>` (e.g. minimal, low, medium, high, xhigh, max) to set
the model's `reasoning_effort` — it is recorded in the run metadata and shown
as `model [effort]` everywhere the run is identified.
Omit `--judge` for a performance-only run (latency/throughput/cost, no
grading). Interrupted runs resume automatically: re-run with the same
`--run-name` **and the same flags** (the run folder pins its config and
refuses a mismatched resume) — cached items are skipped, errored items retry.

### 4. Read the results

Every run writes `results/<run-name>/`:

| File | Contents |
|---|---|
| `results.csv` | one row per question: correct?, confidence, **TTFT**, generation time, **input/output tokens**, **tokens/sec**, **cost (USD)**, model answer |
| `summary.csv` | aggregates overall + per language track + per domain |
| `summary.json` | run metadata + the same aggregates, machine-readable |
| `overview.html` | **open in any browser** — tiles for accuracy, median TTFT, mean tokens/sec, tokens generated, total cost, calibration error, plus per-language/per-domain charts |
| `raw.jsonl` | full per-item records incl. complete responses (the resume cache) |

Metric definitions: TTFT = time from request to first streamed content token;
tokens/sec = output tokens ÷ generation time after the first token; cost =
input_tokens × input price + output_tokens × output price.

> **Note:** until the filtered v1 release ships, runs use the unfiltered
> v0-seed pool — treat scores as diagnostic, not official IndiBench numbers
> (the overview banner says the same).

## Repository layout

```
docs/            Decisions log, project maps, thesis, design docs, research, wiki
src/indibench/   Schema, canary handling, pipeline stages (S0–S5)
scripts/         run_benchmark.py (evaluate a model) · run_filter.py · assemble_candidates.py
evals/           Inspect AI task + standalone predict/judge scripts
data/            Candidate pool + future releases (canary-wrapped)
results/         Your benchmark runs land here (gitignored)
```

## Contributing

- **Found a wrong answer key or bad question?** Open an issue — error
  reporters are credited in release notes and paper acknowledgments.
- **Want to contribute questions?** Direct question submissions aren't
  accepted (it would break the synthetic, adversarially-filtered
  methodology) — but you can contribute *grounding sources* (hard,
  well-licensed Indian documents in any scheduled language) and pipeline
  improvements. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Language expertise welcome:** volunteer domain experts who spot-check
  items earn co-authorship consideration on the paper.

## License

Code: [MIT](LICENSE). Public datasets: CC BY 4.0. The private held-out split
is never published.
