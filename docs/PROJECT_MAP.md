# Project Map — IndiBench

Last updated: 2026-07-13 (alignment phase, after Input 003 — benchmark audit + thesis).
This is the living picture of WHAT we're building and WHERE each workstream stands.
Intent source of truth: `docs/USER_INPUTS.md`. Decision source of truth: `docs/DECISIONS.md`.

## Mission (one line)

Add India to the frontier benchmark suite: **IndiBench** — open, lab-neutral
benchmarks hard enough that today's best models fail them, in Indian languages
and on Indian use cases, across text, speech, vision, and agents.

Thesis: India is a multimodal evaluation problem — see `docs/THESIS.md` (D-024).
Vision: the only benchmark somebody needs in India for any use case (D-026 —
every use case at frontier difficulty; broad-coverage MCQ stays out of scope).

## Identity (D-019, D-021)

**"The open, lab-neutral frontier benchmark for India."**
- Fully public data + harness + generation pipeline (vs IndQA: closed, OpenAI-graded).
- Adversarial filtering against ALL frontier labs' models (OpenAI, Anthropic,
  Google, + Indian models), not one lab's.
- Suite name **IndiBench**; per-phase artifacts IndiBench-Text / -Speech /
  -Vision / -Agent.
- Licenses: MIT (code), CC-BY-4.0 (public data); private held-out split unpublished (D-022).

## Phases (D-016, D-020 — order locked)

| Phase | Artifact | Status | v1 target |
|---|---|---|---|
| 1 | **IndiBench-Text** — frontier knowledge/reasoning, 10–12 langs + code-mixed (Hinglish/Tanglish) | 🟡 Design doc in progress | ~2,500 adversarially-filtered Qs, leaderboard, arXiv paper, inspect_evals registration (D-023) |
| 2 | **IndiBench-Speech** — STT **and TTS/spoken interaction** (D-024), dialect + acoustic diversity | 🔬 Landscape research partial (agent died mid-run; IndicSUPERB/Voice-of-India findings in audit) | TBD (design after Phase 1 ships) |
| 3 | **IndiBench-Vision** — culturally grounded multimodal, BOTH directions: understanding India in images AND historically/contextually accurate image GENERATION (D-024) | ⏳ Roadmap | TBD |
| 4 | **IndiBench-Agent** — Indian-use-case agents (UPI/IRCTC/gov-portal tau2-style domains, tool use, conversational; real-web in scope per D-011, risk review pending) | ⏳ Designed-on-paper from day one; ships last | TBD |

Note: Phase order text > speech > vision > agent was set by the owner in Batch 3
and confirmed in Batch 4 (D-020), superseding the Batch 1 ordering (agents second).
Phase 1 schema carries an optional image field from day one so Phase 3 doesn't
require a schema break.

## Core design (Phase 1)

- **Sourcing (D-009/D-010/D-017):** synthetic — LLM-curated grounding corpus of
  hard Indian source documents (regional-language textbooks, state gazettes,
  case law, exam syllabi as grounding only — never harvested questions) →
  frontier-LLM-authored questions with source-derived answer keys →
  cross-lab adversarial filter (keep only what multiple frontier models fail) →
  human expert spot-check.
- **Contamination (D-013/D-015):** canary GUID per file + private held-out split
  + periodic regeneration (renewable benchmark), LiveBench-style versioning.
- **Harness (D-012):** Inspect AI primary (clone inspect_evals/hle pattern) +
  HLE-style lightweight standalone scripts; easy local runs on Ubuntu.
- **Leaderboard (D-018):** own static leaderboard from day one; court AI4Bharat's
  Indic LLM-Arena for prompt contribution + Phase-4 alignment; arena.ai = BD
  aspiration only.

## Competitive picture (researched 2026-07-12, see docs/research/)

- **Text:** closest competitor OpenAI IndQA (closed-data, culture-only,
  OpenAI-filtered). Our lane: open + cross-lab + STEM/professional depth + Tanglish.
- **Speech:** Voice of India (ASR-only) is a partial incumbent; TTS + spoken
  reasoning appear open — research in flight.
- **Vision:** DRISHTIKON / HinTel-AlignBench exist but not frontier-positioned.
- **Agent:** no incumbent yet; AI4Bharat Indic LLM-Arena Phase 3 is the
  announced closest entrant.

## Development workflow (Input 002, D-014)

- GitHub: https://github.com/pukrvi/indibench (MIT, main protected by convention).
- Feature branches + PRs + sub-agent self-review before merge.
- `benchmarks/` reference repos are gitignored — never committed (clone list in FOLDER_MAP.md).

## Workstream status

| Workstream | Status |
|---|---|
| Alignment loop | 🟡 16 questions asked (Batches 1–4); Batch 5 next (governance, domains, judge panel, refresh cadence, budget) |
| Reference-repo study | ✅ Done |
| Landscape research (text) | ✅ docs/research/2026-07-12-indic-landscape.md |
| Harness research | ✅ docs/research/2026-07-12-harness-and-arena.md |
| **Benchmark audit (Input 003)** | ✅ docs/research/2026-07-13-benchmark-audit.md (20 benchmarks; build-upon/improve synthesis) |
| Thesis | ✅ docs/THESIS.md (D-024) |
| Speech landscape research | 🟠 Partial — research agent killed by API spend limit; core findings captured in audit §12/§19; full sweep to redo before Phase 2 design |
| CLAUDE.md + maps | ✅ Current |
| Git/GitHub dev workflow | ✅ Live (PR #1 merged with sub-agent review) |
| Phase 1 design doc | 🟡 Drafting |
| Repo scaffold for benchmark code | ⏳ After Phase 1 design locks |

## Known open questions (feeding Batch 5+)

- Governance/org: who maintains IndiBench long-term? (personal / org / consortium)
- Phase 1 domain list (which subjects, how many per language?)
- Adversarial panel composition (which models, how many must fail a question?)
- Judge model + protocol for scoring (LLM-judge lab-neutrality!)
- Leaderboard submission verification (self-reported predictions are fabricable — maintainer-run? logs? private-split spot-reruns?)
- Refresh cadence + versioning policy specifics; private held-out split size
- Source-document licensing rules for the grounding corpus (S0)
- Real-website agent tasks: risk decision pending (D-011 ⏳ — reproducibility/legal)
- Budget: API costs for generation/filtering; paid expert spot-checks
- Human baseline collection?
- Safety/bias track: out of scope (Indic-Bias exists) or later phase?
- Role of langfuse (infra intent?) — still unasked
- English-about-India counting inside/on top of 10–12 languages
- Community contributions of questions: accepted? bounty?
- Image-generation accuracy scoring methodology (rubric? VLM-judge? human panel?) — Phase 3, not urgent (D-024 ⏳)
- Historical accuracy as a scored dimension across ALL phases — interpretation in THESIS.md pending owner confirmation
