# IndiBench — AGENTS.md

Open-source **LLM + Agent benchmark for Indian languages and Indian use cases**,
positioned as an addition to the frontier benchmark suite (alongside Humanity's
Last Exam, SWE-bench) — NOT another coding benchmark, and NOT another
broad-coverage MMLU clone.

> Project status: **alignment phase** — scope is being locked through a
> question-by-question alignment loop with the project owner. Nothing below
> should be contradicted without checking `docs/DECISIONS.md` first.

## Read these files first (kept updated — this is a hard rule)

| File | What it is | Update rule |
|------|-----------|-------------|
| `docs/USER_INPUTS.md` | **Verbatim** record of every input the owner has given. The source of truth for intent — consult it instead of guessing what was meant. | Append every new owner input, quoted exactly, never paraphrased. |
| `docs/DECISIONS.md` | The decisions log. Every question asked in the alignment loop, the options offered, the answer given, and the resulting locked decision (D-###). | Append every question batch and answer as it happens. |
| `docs/FOLDER_MAP.md` | Map of what's physically in this folder and why each repo is here. | Update whenever files/folders are added, moved, or removed. |
| `docs/PROJECT_MAP.md` | The project map: what we're building, tracks, phases, current state of each workstream. | Update whenever a decision changes scope or a workstream advances. |

## What we are building (locked so far — see DECISIONS.md for full log)

**IndiBench** (D-021) — "the open, lab-neutral frontier benchmark for India"
(D-019), aiming to be the only benchmark somebody needs in India for any use
case (D-026) — every use case at frontier difficulty, never duplicating
broad-coverage MCQ. Four phases, order locked (D-020): **text > speech >
vision > agent**. Governing thesis: India is a multimodal evaluation problem —
`docs/THESIS.md` (D-024): both directions of voice (STT+TTS) and of vision
(understanding AND historically-accurate image generation) are core, with
historical accuracy a scored dimension throughout. The 20-benchmark audit
(`docs/research/2026-07-13-benchmark-audit.md`, D-025) is binding design
guidance: its Part D lists what we build upon and what we must fix.

- **Phase 1 — IndiBench-Text:** frontier-difficulty questions in 12 language
  tracks (D-031): Hindi, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam,
  Gujarati, Punjabi, Odia, English-about-India, and code-mixed
  (Hinglish/Tanglish), positioned like HLE: today's best models
  should score LOW. v1 = ~2,500 adversarially-filtered questions + leaderboard
  + paper + inspect_evals registration (D-023). Closest competitor is OpenAI's
  IndQA — we differentiate on open data/harness/pipeline and cross-lab
  adversarial filtering.
- **Phase 2 — IndiBench-Speech:** TTS/STT/spoken interaction with dialect and
  acoustic diversity. Landscape research in docs/research/.
- **Phase 3 — IndiBench-Vision:** culturally grounded multimodal (arts,
  festivals, scene text, charts in Indian scripts). Phase 1 schema carries an
  optional image field from day one.
- **Phase 4 — IndiBench-Agent:** Indian-use-case agents (tau2-style UPI/IRCTC/
  gov-portal domains, tool use, conversational; real-website tasks locked into
  scope by D-011 but under risk review). Designed on paper from day one;
  ships last.
- **Sourcing (all phases):** synthetic — questions authored by frontier LLMs,
  **grounded in hard Indian source documents** (regional-language textbooks,
  state gazettes, case law; exam syllabi as grounding only, never harvested
  questions — D-017). Answer keys come from sources, not model memory.
  **Cross-lab adversarial filtering** keeps only items multiple frontier
  models fail; human experts spot-check a sample.
- **Contamination defense:** canary GUID in every public file + private
  held-out split + periodic synthetic regeneration (a "renewable benchmark").
- **Harness:** Inspect AI primary + HLE-style lightweight scripts, easy to run
  locally on Ubuntu. Own leaderboard from day one; AI4Bharat Indic LLM-Arena
  partnership courted (D-018).
- **Licenses:** MIT code, CC-BY-4.0 public data (D-022).

## Out of scope (locked)

- Coding benchmarks (SWE-bench-style) — the reference repo is here for
  structural study only.
- Broad-coverage moderate-difficulty MCQ suites (MILU/BhashaBench own this).

## Working rules for Codex in this repo

1. **Never invent intent.** If a design choice isn't in `docs/DECISIONS.md`,
   it is OPEN — ask the owner (alignment loop style: batched questions,
   recommended option first) rather than assuming.
2. **Record everything.** Every question asked → `docs/DECISIONS.md`. Every
   owner input → `docs/USER_INPUTS.md` verbatim. Keep both maps current.
3. **Work between question batches.** The owner's rule: after ~8 questions,
   stop asking and do real work (research, prototyping, writing) before the
   next batch.
4. **The `benchmarks/` folder is reference material, not our code.** Do not
   modify the cloned repos. Copy patterns out of them (see FOLDER_MAP.md for
   what each is good for).
5. This project will be **open-sourced** — write everything (docs, code,
   commit messages) as if external contributors are reading.
6. **Dev-team workflow (D-014):** the repo is
   https://github.com/pukrvi/indibench. Never commit directly to `main`.
   Every change: feature branch → PR → **self-review by a sub-agent** (spawn a
   reviewer agent on the PR diff; address its findings) → merge. Keep
   `benchmarks/` and `.Codex/` out of git (see `.gitignore`).
