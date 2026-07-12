# Decisions Log — IndiBench Alignment Loop

Status: **IN PROGRESS** — alignment loop running.
Every question asked to the project owner and every answer given is recorded
here, in order. Locked decisions are marked ✅. Open items are marked ⏳.

Sources being reconciled:
- `docs/USER_INPUTS.md` (verbatim owner inputs — source of truth for intent)
- `LMBench_References.md` (curated reference list of benchmark repos)
- `benchmarks/*` (10 cloned reference repos)

---

## Pre-locked from Input 001 (owner's kickoff message)

| # | Decision | Status |
|---|----------|--------|
| D-001 | The project is an open-source LLM + Agent benchmark for Indian languages and Indian use cases. | ✅ |
| D-002 | Coding benchmarks (SWE-bench-style) are OUT of scope. | ✅ |
| D-003 | Goal is to add to the frontier benchmark suite (peers: HLE, SWE-bench) — not to replicate what exists. | ✅ |
| D-004 | Process: alignment loop with batched questions; real work interleaved every ~8 questions. | ✅ |
| D-005 | Maintain: CLAUDE.md, folder/project map, decisions log, verbatim user-inputs file. | ✅ |

---

## Question Batches

(Recorded as asked. Format: Q → options offered → answer → resulting decision.)

### Batch 1 — 2026-07-12 — Keystone scope decisions

**Q1. Primary artifact shape?** Options: dual-track phased (recommended) / knowledge-only / agentic-only / both at equal priority.
**Answer:** Dual-track, phased. → **D-006 ✅** Track 1 = frontier-difficulty knowledge/reasoning in Indian languages (HLE-style); Track 2 = agentic tasks on Indian use cases. Track 1 ships first; both designed from day one. *(Ordering half superseded by D-020: agents now Phase 4, after speech and vision.)*

**Q2. Difficulty positioning of the knowledge track?** Options: frontier-hard (recommended) / broad-moderate / tiered.
**Answer:** Frontier-hard. → **D-007 ✅** Questions where today's best models score low. Explicitly NOT competing with MILU/BhashaBench broad coverage.

**Q3. Language strategy for v1?** Options: ~10-12 langs + code-mixed (recommended) / Hindi+English first / all 22 scheduled.
**Answer:** ~10-12 languages + code-mixed. → **D-008 ✅** ~10–12 major languages plus code-mixed (Hinglish/Tanglish); schema designed to extend to all 22 scheduled languages. *(The specific list — Hindi, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia + English-about-India — comes from the selected option's description; final list and whether English-about-India counts inside or on top of the 10–12 to be confirmed in a later batch.)*

**Q4. Question/task sourcing?** Options: expert+exam hybrid (recommended) / expert-only / exam-harvested / synthetic+human-verified.
**Answer (owner's own wording):** "Synthetic: LLM Sourced and Then Frontier LLM only create it." → **D-009 ✅** Sourcing is synthetic: source material mined/curated by LLMs, questions authored by frontier LLMs. ⚠️ Tension with D-007 (frontier-hard) noted — resolution asked in Batch 2 (how do frontier models author questions frontier models fail?).

### Batch 2 — 2026-07-12 — Difficulty mechanics, agent shape, harness, contamination

**Q5. How can frontier-LLM-authored questions stay frontier-hard with trustworthy answer keys?** Options: grounded+adversarial filter (recommended) / multi-model cross-verification only / full human verification / composition-based difficulty.
**Answer:** Grounded + adversarial filter. → **D-010 ✅** Questions generated grounded in hard source documents (regional-language textbooks, state gazettes, case law, local records) so the answer key comes from the source, not the model's parametric memory. Adversarial filtering keeps only items multiple frontier models fail. Human experts spot-check a sample. *(The ~10% spot-check ratio comes from the selected option's description — treat as a Claude-proposed default, tunable later.)* This resolves the D-007/D-009 tension.

**Q6. Agent-track shape? (multi-select)** Options: simulated Indian environments / tool-use scenarios / multilingual conversational agents / real-website tasks.
**Answer:** All of the above. → **D-011 ✅** Agent track will eventually span all four modalities. ⏳ Phasing order to be proposed by Claude and confirmed *(resolved: agent track is Phase 4 per D-020)*; real-website tasks carry reproducibility/legal risks — flagged, still ⏳.

**Q7. Evaluation harness?** Options: Inspect AI primary (recommended) / lm-eval-harness / HLE-style custom scripts / custom + langfuse.
**Answer (owner's own wording):** "Inspect AI, HLE, Lm Arena". → **D-012 ✅ (partial)** Inspect AI as primary framework + HLE-style lightweight standalone scripts. ⏳ "LM Arena" needs clarification — arena-style human-preference evaluation is a different modality; researching what LM Arena integration means before asking follow-up (Batch 3). *(LM-Arena part resolved by D-018.)*

**Q8. Contamination strategy?** Options: canary+private+refresh (recommended) / canary only / fully private submission-based.
**Answer:** Canary + private held-out + refresh. → **D-013 ✅** Three layers: canary GUID in every public file; private held-out split for memorization detection; periodic synthetic regeneration ("renewable benchmark") as a differentiator.

---

**Work interleave 1 (after Q8, per owner's every-8-questions rule):** web research on (a) 2025–26 Indic benchmark landscape — is the frontier-Indic or agent-Indic niche already occupied; (b) Inspect AI agent-eval maturity, LM Arena integration model, renewable-benchmark precedents (LiveBench etc.). Plus: initial CLAUDE.md, FOLDER_MAP.md, PROJECT_MAP.md.

---

## Input 002 (goals.md + GitHub repo) — new decisions & new conflicts

| # | Decision | Status |
|---|----------|--------|
| D-014 | Development runs like a dev team on https://github.com/pukrvi/indibench: feature branches, PRs, sub-agent self-review before merge. | ✅ |
| D-015 | Repo hygiene per goals.md: canary strings in datasets, eval scripts easy to run locally on Ubuntu (incl. small local models), clear open licensing. Consistent with D-013. *(goals.md names MIT / CC-BY-4.0 as examples; the exact code/data license split is still open — Batch 3/4.)* | ✅ (licenses ⏳) |
| C-001 | **CONFLICT:** goals.md adds Vision/Multimodal and Speech (TTS/STT) tracks; Batch 1 locked a dual-track scope (knowledge + agentic). Reconcile: are these v1 tracks, later phases, or aspirational? | ⏳ Batch 3 |
| C-002 | **CONFLICT:** goals.md says "material from regional and state-level examinations" and MILU-style "all 22 scheduled languages"; D-009 locked synthetic sourcing, D-008 locked 10–12 langs for v1. Reconcile: exams as *grounding source docs* for synthesis (compatible) vs harvested questions (contradicts D-009)? 22 languages as end-goal (compatible) vs v1 (contradicts D-008)? | ⏳ Batch 3 |

**Work interleave 1 results (full reports in `docs/research/`):**
- Landscape: Track 1 niche partially occupied by OpenAI IndQA (closed-data,
  culture-only, OpenAI-filtered) — open differentiators: open data, cross-lab
  adversarial filtering, document-grounded synthesis at scale, STEM/professional
  depth, Tanglish. Track 2 has NO incumbent. Speed matters (AI4Bharat/BharatGen
  likely next movers).
- Harness: Inspect AI confirmed sound primary (HLE already implemented in
  inspect_evals); tau2-style domains cheapest for Indian agent environments;
  **LM Arena has no third-party contribution path** — realistic option is
  partnering with AI4Bharat's Indic LLM-Arena (Nov 2025; Phase 3 = agentic).

### Batch 3 — 2026-07-12 — goals.md reconciliation, arena strategy, IndQA positioning

**Q9. Modalities: reconcile goals.md's vision+speech with locked dual-track (C-001)?** Options: phased text→agent→vision→speech (recommended) / vision in v1 / all four in v1 / text-only.
**Answer (owner's own wording):** "phased: text > speech > vision > agent". → **D-016 ✅ (pending confirmation of one consequence)** Four phases: Phase 1 text (frontier knowledge/reasoning), Phase 2 speech (TTS/STT), Phase 3 vision/multimodal, Phase 4 agentic. ⚠️ **Supersedes the ordering half of D-006** (which had agentic shipping second): the agent track moves to Phase 4. C-001 resolved (all goals.md modalities are in, phased). Confirmation of the agent-track deferral asked in Batch 4.

**Q10. goals.md exam material + 22 languages vs D-008/D-009 (C-002)?** Options: exams-as-grounding-docs + 22-as-end-goal (recommended) / goals.md wins (reversal) / hybrid tagged exam subset.
**Answer:** Exams as grounding docs; 22 as end-goal. → **D-017 ✅** Exam syllabi/materials are GROUNDING DOCUMENTS for the synthetic pipeline, never harvested questions (D-009 intact). "All 22 scheduled languages" is the roadmap end-state; v1 ships 10–12 (D-008 intact). C-002 resolved.

**Q11. Arena/leaderboard strategy?** Options: own leaderboard + court AI4Bharat (recommended) / leaderboard only / partnership-first.
**Answer:** Own leaderboard + court AI4Bharat. → **D-018 ✅** Ship our own leaderboard (GitHub Pages / HF Space) from day one; approach AI4Bharat about contributing frontier-hard prompts to Indic LLM-Arena and aligning the agentic phase with their Phase 3. arena.ai is BD aspiration only, not a milestone. Resolves the LM-Arena part of D-012.

**Q12. Lead differentiator vs IndQA?** Options: open + cross-lab (recommended) / STEM-professional depth / code-mixed frontier / synthetic scale.
**Answer:** Open + cross-lab. → **D-019 ✅** Identity: "the open, lab-neutral frontier benchmark for India" — public data+harness+pipeline; adversarial filtering against ALL frontier labs' models incl. Indian models. Balanced domain mix (culture AND STEM/professional). Other differentiators (Tanglish, scale) are supporting, not headline.

### Batch 4 — 2026-07-12 — Phasing confirmation, name, licenses, v1 target

**Q13. Confirm agent-track deferral to Phase 4 (supersedes D-006 ordering)?** Options: yes text>speech>vision>agent / restore text>agent / parallel middle path.
**Answer:** Yes — text > speech > vision > agent. → **D-020 ✅** Phase order LOCKED: 1 Text, 2 Speech, 3 Vision, 4 Agent. D-006's ordering is formally superseded (recorded here, not silently). Agent track remains designed-on-paper from day one (schema + domain list) so Phase 4 starts warm. Speech overlap noted: Voice of India (2026) is ASR-only; TTS + spoken-reasoning remain open.

**Q14. Final name?** Options: IndiBench (recommended) / different name / decide at launch.
**Answer:** IndiBench. → **D-021 ✅** Suite name: **IndiBench**; per-phase artifacts: IndiBench-Text, IndiBench-Speech, IndiBench-Vision, IndiBench-Agent.

**Q15. Licensing?** Options: MIT code + CC-BY-4.0 data (recommended) / MIT + CC-BY-SA / all MIT.
**Answer:** MIT code + CC-BY-4.0 data. → **D-022 ✅** Code MIT (already in repo); public datasets CC-BY-4.0; private held-out split unpublished/unlicensed. Closes the license part of D-015.

**Q16. Phase 1 v1 target?** Options: ~2,500 filtered Qs + leaderboard + paper (recommended) / ~1,000 fast v0.5 / 5,000+.
**Answer:** ~2,500 filtered Qs, leaderboard, paper. → **D-023 ✅** v1 = ~2,500 questions surviving cross-lab adversarial filtering, across 10–12 languages + code-mixed; public leaderboard; arXiv paper; inspect_evals registration.

---

**Work interleave 2 (after Q16):** record batch; update maps/CLAUDE.md; speech-landscape research (Phase 2 due diligence); draft Phase 1 (IndiBench-Text) design doc; PR #2 with sub-agent review.

---

## Input 003 (audit directive + multimodal thesis) — new decisions

| # | Decision | Status |
|---|----------|--------|
| D-024 | **The IndiBench thesis** (owner, Input 003): multimodality is disproportionately important for India — visual understanding of India, contextually/historically **accurate image output**, language understanding, voice-to-text, voice-to-speech. Adopted as `docs/THESIS.md`; underwrites the four-phase suite (D-020). Phase 3 scope now explicitly includes image-GENERATION evaluation, Phase 2 includes both STT and TTS directions. *(Resolves the image-generation scope flag raised in USER_INPUTS Input 003 interpretation.)* | ✅ |
| D-025 | Benchmark audit delivered: `docs/research/2026-07-13-benchmark-audit.md` — 20 benchmarks audited (right/wrong per benchmark); Part D build-upon/improve synthesis is binding design guidance. Four trusted references cloned into `benchmarks/` (IndicXTREME via IndicBERT, IndicSUPERB, MASSIVE, COMI-LINGUA stub). | ✅ |
| D-026 | "Only benchmark somebody needs in India for any use case" (owner vision, Input 003) = every use case covered at frontier difficulty across the four phases — NOT duplicating broad-coverage MCQ (D-003/D-007 unchanged). | ✅ |

⏳ New open item from D-024: how to *score* image-generation cultural/historical
accuracy (rubric? VLM-judge? human panel?) — Phase 3 design question, to be
asked when Phase 3 design starts (noted, not urgent for Phase 1).

### Batch 5 — 2026-07-13 — Thesis confirmation, governance, panel, domains

**Q17. Historical accuracy as scored dimension across ALL phases (THESIS.md interpretation)?** Options: yes all phases (recommended) / images only / per-phase at design time.
**Answer:** Yes — all phases. → **D-027 ✅** Historical/factual accuracy about India is a tagged, reportable dimension suite-wide: Phase 1 historical domain slice, Phase 3 period/cultural correctness of generated images, Phase 2 spoken answers. THESIS.md interpretation flag resolved.

**Q18. Governance?** Options: personal → org later (recommended) / dedicated org now / institutional home first.
**Answer:** Personal → org later. → **D-028 ✅** v1 ships from pukrvi/indibench; on traction (paper + leaderboard) migrate to a dedicated GitHub org and invite 2–3 co-maintainers.

**Q19. Adversarial panel + threshold?** Options: 3 labs + 1 Indian model, keep if ≥2/4 fail (recommended) / all-fail / majority of 6–8.
**Answer:** 3 labs + 1 Indian model; keep if ≥2 fail. → **D-029 ✅** Panel: one frontier model each from OpenAI, Anthropic, Google + best Indian model (e.g., Sarvam). Keep questions ≥2 of 4 fail. Dual-judge from two labs with third-judge tiebreak. Panel composition published.

**Q20. Phase 1 domain taxonomy?** Options: 10-domain balanced grid (recommended) / professional-heavy / culture-heavy / data-decides.
**Answer:** 10-domain balanced grid. → **D-030 ✅** Domains: law & constitution · governance & administration · STEM-in-India · medicine incl. Ayush · finance & taxation · agriculture · history & heritage · regional literature & arts · geography & environment · society & daily life. Roughly equal per-language quotas; grid published.

### Batch 6 — 2026-07-13 — Languages final, refresh, budget, human baseline

**Q21. Final v1 language list + English counting?** Options: 12 = 10 Indic + en-IN + code-mixed (recommended) / add Urdu+Assamese (14) / trim to 8.
**Answer:** 12 tracks. → **D-031 ✅** Hindi, Bengali, Tamil, Telugu, Marathi, Kannada, Malayalam, Gujarati, Punjabi, Odia + English-about-India (11th track) + code-mixed Hinglish & Tanglish (12th track). Native authoring only. Urdu/Assamese/others in refresh waves toward all 22. Closes D-008's open note.

**Q22. Refresh cadence + private split?** Options: 6-monthly/~20% (recommended) / quarterly/~15% / annual/~25%.
**Answer:** 6-monthly; ~20% private. → **D-032 ✅** Two waves/year replacing ~1/3 of public items (oldest/easiest first), stable anchor subset; private held-out ≈500 questions, never released.

**Q23. Budget envelope?** Options: bootstrap <$5k + volunteers / seed $5–25k (recommended) / wait for funding.
**Answer:** Bootstrap: <$5k API + volunteer experts. → **D-033 ✅** Efficient generation models, aggressive caching, panel calls only on pre-screened candidates; experts recruited for co-authorship credit (HLE-style academic incentive), not pay. Pipeline design must be cost-aware end-to-end.

**Q24. Human baseline for the paper?** Options: small calibration baseline (recommended) / full study / skip for v1.
**Answer:** Skip for v1. → **D-034 ✅** v1 ships model scores only; human baseline added in a later refresh wave. "Frontier-hard" claim rests on adversarial-filter construction (D-029). Consistent with D-033 volunteer-budget reality.

---

**Work interleave 3 (after Q24):** record batch; propagate locked parameters into the Phase 1 design doc (panel, domains, tracks, refresh, cost-aware pipeline); prune resolved open items from PROJECT_MAP; PR #4 with sub-agent review.

### Batch 7 — (pending)
