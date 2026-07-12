# User Inputs — Verbatim Record

This file preserves the original, verbatim inputs from the project owner so the
original intent can always be consulted directly, rather than reconstructed.
Newest entries at the bottom. Never paraphrase into this file — quote exactly.
Owner answers to alignment-loop question batches are ALSO recorded here
verbatim (the exact option label or free-text the owner selected/typed);
the full question context lives in `DECISIONS.md`.

---

## Input 001 — 2026-07-12 — Project kickoff

> I want to create an LLM AI and Agent Benchmark for Indian Languages and Use
> Cases. The folder contains a bunch of open-source repos of popular LLM
> benchmarks and some Indian benchmarks which we already have. I want you to
> first figure out what we want to do because we are going to open-source this
> project. We should not be getting into regular coding benchmarks like that.
> We should just focus on adding to the current suite of benchmarks, like
> Humanities Last Exam or SWE Bench. We have to then just keep focused on that.
>
> We will run the alignment loop to figure out what needs to be done. You can
> ask me as many questions as you want. Ask it:
> 1. When you have first read the folder, ask me questions.
> 2. Think on those questions.
> 3. Work some more.
> 4. Search on the internet.
> 5. Come back to me and ask more questions.
> Don't just ask questions upfront. Do some work every time you have asked me
> 8 questions.
>
> Write a claude.md, folder map and structure and all the decisions which you
> ask me through the alignment loop: every time you ask me a question, record
> that. Create a bunch of these files and mention that in Claude.md:
> 1. These files are updated, which is a folder map and the project map.
> 2. All the inputs which I have provided, so the original intention of my
>    inputs can always be looked at rather than you trying to figure out what
>    needs to be done.

**Working interpretation (not verbatim — see quote above for source of truth):**
- Build an open-source LLM + Agent benchmark for Indian languages and Indian
  use cases.
- Do NOT build a coding benchmark (SWE-bench-style coding is out of scope);
  the goal is to ADD an Indian benchmark to the frontier suite alongside
  benchmarks like Humanity's Last Exam and SWE-bench.
- Process: alignment loop — read folder → ask questions in batches → work →
  internet research → more questions. Do real work between every ~8 questions.
- Deliverables of the alignment phase: CLAUDE.md, folder map / project map
  (kept updated), decisions log (every question + answer recorded), and this
  verbatim inputs file.

---

## Input 001a — 2026-07-12 — Batch 1 answers (verbatim selections)

> Q1 (primary artifact): "Dual-track, phased (Recommended)"
> Q2 (difficulty): "Frontier-hard (Recommended)"
> Q3 (languages): "~10-12 langs + code-mixed (Recommended)"
> Q4 (sourcing, owner's own text): "Synthetic: LLM Sourced and Then Frontier
> LLM only create it."

## Input 001b — 2026-07-12 — Batch 2 answers (verbatim selections)

> Q5 (hard-synthetic mechanics): "Grounded + adversarial filter (Recommended)"
> Q6 (agent-track shape, multi-select): "All of the above"
> Q7 (harness, owner's own text): "Inspect AI, HLE, Lm Arena"
> Q8 (contamination): "Canary + private held-out + refresh (Recommended)"

---

## Input 002 — 2026-07-12 — goals.md + GitHub repo + dev workflow

Owner shared `goals.md` — that file, committed at the repo root, IS the
verbatim input; consult it directly. And said (verbatim):

> Understand the goals and here's the repo for the same so start maintaining
> it yourself like a dev team. proper branching, PRs and Self-Review by
> Sub-Agent.
> https://github.com/pukrvi/indibench

**Working interpretation:**
- `goals.md` broadens candidate scope with vision/multimodal + speech tracks —
  needs reconciliation with the locked dual-track decision (D-006) → to be
  asked in the next batch, not silently adopted.
- goals.md's "material from regional and state-level examinations" and "all 22
  scheduled languages" sit in tension with D-009 (synthetic sourcing) and
  D-008 (10–12 languages in v1) → flagged for reconciliation. *(Both resolved
  in Batch 3 → D-017.)*
- Repo-structure requirements (canary, runnable-on-Ubuntu eval scripts, MIT /
  CC-BY-4.0) are consistent with D-013 and prior direction — treat as locked.
- Development workflow from now on: git with feature branches, PRs on
  https://github.com/pukrvi/indibench, and sub-agent self-review before merge.

---

## Input 002a — 2026-07-12 — Batch 3 answers (verbatim selections)

> Q9 (modalities vs C-001, owner's own text): "phased: text > speech > vision > agent"
> Q10 (goals.md vs locked decisions, C-002): "Exams as grounding docs; 22 as end-goal (Recommended)"
> Q11 (arena strategy): "Own leaderboard + court AI4Bharat (Recommended)"
> Q12 (lead differentiator vs IndQA): "Open + cross-lab (Recommended)"

## Input 002b — 2026-07-12 — Batch 4 answers (verbatim selections)

> Q13 (confirm phasing, supersedes D-006 ordering): "Yes — text > speech > vision > agent"
> Q14 (name): "IndiBench (Recommended)"
> Q15 (licenses): "MIT code + CC-BY-4.0 data (Recommended)"
> Q16 (Phase 1 v1 target): "~2,500 filtered Qs, leaderboard, paper (Recommended)"

---

## Input 003 — 2026-07-13 — Benchmark audit directive + multimodal thesis

> Furst do a research and review of all the indian benchmarks which are in
> folder. If you find some trusted big ones online from research, download
> them as well.
>
> Audit them.
> Find what they did right and what they did wrong, so audit each of them.
> Then figure out, from what they have done right, what we should build upon
> and, from what they have done wrong, what we should improve to make
> indibench the only benchmark somebody needs in India for any use case.
>
> Also have one thesis that, in India, apart from all the usual LLM benchmarks
> and stuff, multi-modal is very important: understanding India visually
> through images, or even then output images contextually which are correct
> from India. Historical accuracy, language understanding, voice-to-text,
> voice-to-speech: they are the very big part, so indibench should definitely
> do that.

**Working interpretation:**
- Deliverable: a per-benchmark audit (right/wrong) of every Indian benchmark
  in `benchmarks/`, extended with trusted major Indian benchmarks found
  online (cloned into `benchmarks/` — reference-only, gitignored), and a
  synthesis: build-upon list + improve list, aimed at "the only benchmark
  somebody needs in India for any use case".
- Vision statement: IndiBench = one-stop suite for India across use cases —
  consistent with the repo README tagline; achieved via the four-phase
  multimodal suite + frontier difficulty, NOT by rebuilding broad MCQ
  coverage (D-003/D-007 unchanged).
- Thesis (owner): multimodality is disproportionately important for India —
  visual understanding of India, contextually/historically accurate
  image OUTPUT, language understanding, voice-to-text, voice-to-speech.
  Reinforces phases 2–3 (D-016/D-020). ⚠️ New scope element spotted:
  evaluating image GENERATION (not just understanding) — not covered by any
  locked decision → to be asked in a coming batch.
