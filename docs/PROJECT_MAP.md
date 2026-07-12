# Project Map — IndiBench

Last updated: 2026-07-12 (alignment phase, after Input 002 — goals.md + GitHub repo — and work interleave 1).
This is the living picture of WHAT we're building and WHERE each workstream stands.
Intent source of truth: `docs/USER_INPUTS.md`. Decision source of truth: `docs/DECISIONS.md`.

## Mission (one line)

Add India to the frontier benchmark suite: a benchmark hard enough that today's
best models fail it, in Indian languages and on Indian use cases — plus the
first serious agentic benchmark for Indian digital life.

## Positioning

| | Existing (MILU, BhashaBench, IndicGenBench) | IndiBench |
|---|---|---|
| Difficulty | Broad coverage, models score high | Frontier-hard — models score LOW (D-007) |
| Peer group | MMLU, IndicGLUE | HLE, SWE-bench-class suite (D-003) |
| Agents | None | Core track (D-006) |
| Sourcing | Harvested past exams (contaminated) | Synthetic, grounded, adversarially filtered (D-009/D-010) |
| Lifespan | Static | Renewable via regeneration (D-013) |

## Tracks

### Track 1 — Frontier Knowledge & Reasoning (ships first)
- ~10–12 major Indian languages + English-about-India + code-mixed
  Hinglish/Tanglish (D-008). Schema extensible to all 22 scheduled languages.
- Synthetic pipeline: LLM-mined source docs → frontier-LLM-authored questions
  grounded in those docs → adversarial filter (keep only what multiple frontier
  models fail) → ~10% human expert spot-check (D-010).
- Contamination: canary GUID + private held-out split + periodic regeneration (D-013).
- Harness: Inspect AI task + HLE-style standalone scripts (D-012, partially open).

### Track 2 — Indian Agentic Tasks (designed now, ships second)
- All four modalities eventually (D-011): simulated Indian environments
  (UPI/IRCTC/gov portals), tool-use/function-calling scenarios, multilingual
  conversational agents, real-website tasks (⚠️ reproducibility/legal concerns
  flagged; phasing order not yet confirmed).

## Competitive picture (researched 2026-07-12, see docs/research/)

- **Track 1 closest competitor: OpenAI IndQA** (Nov 2025; 2,278 Q, 12 langs incl.
  Hinglish, GPT-5 ≈ 35%) — but closed-data, culture-only, OpenAI-filtered.
  Our open differentiators: open data+harness, cross-lab adversarial filtering,
  document-grounded synthesis at scale, STEM/professional depth, Tanglish.
- **Track 2: no incumbent anywhere.** Closest are MASSIVE-Agents (function
  calling, no environments/Indian services) and Ticket-Bench (zero Indic).
- **Harness verdict:** Inspect AI primary (HLE already in inspect_evals);
  tau2-bench-style mock domains for UPI/IRCTC/gov-portal agent tasks;
  LM Arena proper has no third-party path — AI4Bharat's Indic LLM-Arena
  (Phase 3 = agentic) is the realistic partner/watch-item.

## Development workflow (Input 002)

- GitHub: https://github.com/pukrvi/indibench (MIT license, main branch).
- Feature branches + PRs + sub-agent self-review before merge (D-014).
- `benchmarks/` reference repos are gitignored — never committed.

## Workstream status

| Workstream | Status |
|---|---|
| Alignment loop | 🟡 In progress — 8 questions asked (Batches 1–2); Batch 3 next (goals.md conflicts C-001/C-002, arena strategy, naming/governance) |
| Reference-repo study | ✅ Done |
| Landscape research (is the niche open?) | ✅ Done — docs/research/2026-07-12-indic-landscape.md |
| Harness research (Inspect AI / LM Arena / renewable precedents) | ✅ Done — docs/research/2026-07-12-harness-and-arena.md |
| CLAUDE.md + maps | ✅ Created, kept current |
| Git/GitHub dev workflow | 🟡 Being set up (first PR in flight) |
| Benchmark naming, org, license, governance | ⏳ Batch 3/4 |
| Pipeline design doc | ⏳ Blocked on remaining alignment answers |
| Repo scaffold for our own code | ⏳ Blocked on alignment close |

## Known open questions (feeding future batches)

- C-001: goals.md multimodal + speech tracks vs locked dual-track scope — v1, phased, or aspirational?
- C-002: goals.md exam material + 22 languages vs locked synthetic sourcing + 10–12 langs.
- Arena strategy: partner with AI4Bharat Indic LLM-Arena? own leaderboard?
- Agent-track phasing order + real-web risk decision (D-011 ⏳)
- IndQA differentiation emphasis (which of the five differentiators leads?)
- Name confirmation ("IndiBench"?), org/governance, data license (CC-BY-4.0?)
- English-about-India: separate language track or folded in?
- Safety/bias: in scope or leave to Indic-Bias?
- v1 size targets, human baseline collection, budget/timeline
- Role of langfuse (it's in the folder — infra intent?)
