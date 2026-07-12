# IndiBench — CLAUDE.md

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

- **Track 1 — Knowledge/Reasoning (ships first):** frontier-difficulty
  questions in ~10–12 major Indian languages (final list pending; includes
  English-about-India) + code-mixed (Hinglish/Tanglish), positioned like HLE:
  today's best models should score LOW. Not competing with MILU/BhashaBench
  on breadth — competing on difficulty and Indian depth.
- **Track 2 — Agentic:** agent tasks on Indian use cases (simulated
  environments like UPI/IRCTC/gov portals, tool-use scenarios, multilingual
  conversational agents; real-web under review). Designed from day one,
  shipped after Track 1.
- **Sourcing:** synthetic — source material mined/curated by LLMs, questions
  authored by frontier LLMs, **grounded in hard Indian source documents**
  (regional-language textbooks, state gazettes, case law) so answer keys come
  from sources, not model memory. **Adversarial filtering** keeps only items
  multiple frontier models fail; human experts spot-check a sample.
- **Contamination defense:** canary GUID in every public file + private
  held-out split + periodic synthetic regeneration (a "renewable benchmark").
- **Harness:** Inspect AI primary + HLE-style lightweight scripts; LM Arena
  involvement under research (see DECISIONS.md D-012).

## Out of scope (locked)

- Coding benchmarks (SWE-bench-style) — the reference repo is here for
  structural study only.
- Broad-coverage moderate-difficulty MCQ suites (MILU/BhashaBench own this).

## Working rules for Claude in this repo

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
   `benchmarks/` and `.claude/` out of git (see `.gitignore`).
