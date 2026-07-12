# Research: Harness, LM Arena, Renewable Benchmarks, Agent Environments

Date: 2026-07-12 · Work interleave 1 (after question Batch 2) · Web research, sources cited inline.

## Verdicts

1. **Inspect AI is the right primary harness for both tracks.** UK AISI framework;
   Task = dataset + solver + scorer; first-class agent/tool/sandbox support
   (Docker/K8s/Modal); `model_graded_qa()` for LLM-judge; adopted by Anthropic,
   Google DeepMind, xAI, METR, other AISIs. **HLE is already implemented in
   `inspect_evals`** — including the confidence/calibration-error scorer — a direct
   template for Track 1. (https://inspect.aisi.org.uk/,
   https://github.com/UKGovernmentBEIS/inspect_evals)
2. **inspect_evals registration (post-May-2026 process):** open a GitHub issue with
   arXiv URL + our repo link; a bot validates and lists the eval while we keep our
   own repo. We get distribution without giving up control.
3. **LM Arena (now "Arena", arena.ai): no public process for third parties to add
   arenas/categories/regional leaderboards.** Language leaderboards are cut post-hoc
   from organic traffic — curated prompt sets cannot be injected. Realistic options:
   (a) partner with **AI4Bharat's Indic LLM-Arena** (launched Nov 2025,
   arena.ai4bharat.org; Bradley-Terry rankings on Indic + code-mixed prompts;
   **Phase 3 = agentic tasks — overlaps our Track 2**); (b) mine Arena's released
   preference datasets for real Indic prompts; (c) treat an arena.ai India category
   as aspirational BD only. (https://ai4bharat.iitm.ac.in/blog/indic-llm-arena)
4. **HLE recipe has NOT been replicated for any language/region** as of mid-2026 —
   the "frontier-hard Indic" niche is open. HLE's ops model is copyable: bug-bounty
   window, rolling-corrections fork (`hle-rolling`), private held-out split,
   official leaderboard hosted at Scale Labs. Cautionary tale: FutureHouse audit
   found high wrong-answer rates in parts of HLE → answer-key QA is existential.
5. **Renewable-benchmark versioning pattern to copy (LiveBench et al.):**
   date-stamped releases (`v2026.07`), partial refresh with a stable anchor subset,
   private embargo window for new items, delayed archival of old items, full model
   re-runs per release (never mix scores across versions).
   (https://github.com/livebench/livebench, https://www.forecastbench.org/)
6. **Agent environments: tau2-bench-style domains are the cheapest verifiable path**
   for Indian mocks. A domain = policy doc + Python tool functions over a seeded
   JSON DB + tasks + LLM user simulator; verification = deterministic final-DB-state
   comparison + expected-action checks + pass^k. UPI (payments/mandates/disputes),
   IRCTC (booking/tatkal/refunds), gov-portal (DigiLocker/Aadhaar workflows) map
   exactly onto this. Run them as Inspect agent tasks. WebArena-style hosted web
   apps are overkill for v1. Amazon's τ²-Bench-Verified episode ⇒ budget for
   task/policy/DB alignment QA. Keep verification on world-state, not conversation
   quality (LLM-simulated users are unreliable proxies —
   https://arxiv.org/pdf/2601.17087). (https://github.com/sierra-research/tau2-bench)

## Recommended architecture (pending owner confirmation)

- **Track 1:** Inspect task cloning `inspect_evals/hle` pattern; exact-match where
  possible, model-graded QA + confidence elicitation elsewhere; accuracy +
  calibration error. IndiBench-Rolling fork for corrections; LiveBench-style
  versioned refreshes; private held-out split (report existence, not scores).
- **Track 2:** tau2-style domains (policies in English + Hindi + code-mixed;
  Hindi/Hinglish user simulator) run as Inspect agent tasks; deterministic
  final-state scoring; pass^k. Optionally ship native tau2 configs too.
- **Arena involvement:** pursue AI4Bharat Indic LLM-Arena partnership; don't
  promise arena.ai integration as a technical milestone.
