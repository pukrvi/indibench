# User Inputs — Verbatim Record

This file preserves the original, verbatim inputs from the project owner so the
original intent can always be consulted directly, rather than reconstructed.
Newest entries at the bottom. Never paraphrase into this file — quote exactly.

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

## Input 002 — 2026-07-12 — goals.md + GitHub repo + dev workflow

Owner shared `goals.md` (committed at repo root — that file IS the verbatim
input; summary of its five sections: (1) Language & Text Understanding —
multilingual coverage à la MILU/22 scheduled languages, complex reasoning in
native scripts, generation tasks à la IndicGenBench; (2) Vision & Multimodal —
culturally grounded image+text pairs (arts, festivals, attire, architecture,
cuisine across states/UTs), captioning, scene text, charts/tables in Indian
scripts; (3) Speech TTS/STT — spontaneous real-world audio, demographic/dialect
spread across districts; (4) Cultural/Legal/Factual Knowledge — regional &
state-exam material, domains: Social Sciences, STEM, Business, Governance;
(5) Repo & paper structure — canary strings, easy-to-run eval scripts (Ubuntu,
local small models), open licensing MIT/CC-BY-4.0.)

And said (verbatim):

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
  D-008 (10–12 languages in v1) → flagged for reconciliation.
- Repo-structure requirements (canary, runnable-on-Ubuntu eval scripts, MIT /
  CC-BY-4.0) are consistent with D-013 and prior direction — treat as locked.
- Development workflow from now on: git with feature branches, PRs on
  https://github.com/pukrvi/indibench, and sub-agent self-review before merge.
