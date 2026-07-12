# Audit: Indian & Reference Benchmarks — What They Did Right, What They Did Wrong

Date: 2026-07-13 · Owner directive (Input 003): audit every Indian benchmark in
`benchmarks/`, plus trusted major ones found online; derive what IndiBench
builds upon and what it must improve to be *the only benchmark somebody needs
in India for any use case*.

Sources: direct repo inspection (`benchmarks/`), papers/READMEs, and the dated
research reports in this folder. Repos marked *-ref* were added for this audit
(shallow clones, gitignored like the rest).

---

## Part A — Benchmarks in the folder

### 1. MILU (AI4Bharat, NAACL 2025) — `MILU-master`
**What:** ~80k MCQs, 11 languages, 8 domains/41 subjects, from Indian regional/state exams.
**Did right:**
- Per-language × per-domain reporting surface; group roll-ups weighted by size — the right way to report a multilingual benchmark.
- lm-eval-harness task packaging (`_default_template_yaml` + per-language YAMLs) — anyone can run it in one command.
- Separate validation split for few-shot exemplars (5-shot, `first_n` sampler) — no test leakage into prompts.
- ~25% human-translated items to fill low-resource gaps, transparently tagged per language.
- Gated HF distribution (friction against training-data scraping) + CC-BY-4.0.
**Did wrong / limits:**
- Harvested from published exams → the questions (and answer keys) are on the public internet → contaminated for any model trained on Indian web data. No canary, no private split, no refresh plan.
- Difficulty saturated on arrival: GPT-4o ~72–74%. It measures deployment competence, not frontier progress.
- MCQ-only, log-likelihood scoring — never tests generation, reasoning chains, or code-mixing.
- No contamination audit in the paper despite exam sourcing being the obvious risk.
**IndiBench takes:** the packaging/reporting pattern (build upon); the sourcing and difficulty ceiling (improve via synthetic grounded generation + adversarial filtering, D-009/D-010).

### 2. BhashaBench V1 (BharatGen, Oct 2025) — `BhashaBench-main`
**What:** ~74k domain QA (agriculture/finance/legal/Ayurveda), English + Hindi, from 130+ government exams.
**Did right:**
- Domain depth as the organizing axis — professional Indian domains (Krishi, legal, Ayur) that global benchmarks never touch. This is the single most India-authentic design idea in the folder.
- Difficulty + question-type + subdomain metadata per item enables sliced analysis.
- Clean fork-of-MILU repo pattern — proves the packaging is replicable per domain.
**Did wrong / limits:**
- Only English + Hindi — "Bhasha"Bench without 20 of the 22 scheduled languages.
- Same exam-harvest contamination exposure as MILU; gated HF but no canary/private split.
- 0-shot MCQ log-likelihood only; scores already 60–77% for GPT-4o → not frontier.
- Code license is a leftover EleutherAI MIT header — sloppy provenance hygiene.
**IndiBench takes:** professional-domain axis for our domain taxonomy (build upon); language breadth + difficulty positioning (improve).

### 3. IndicGenBench (Google Research, 2024) — `indic-gen-bench-main`
**What:** generation tasks (cross-lingual summarization, MT, QA) across 29 Indic languages via human translation of existing datasets.
**Did right:**
- **Canary GUID in every data file** (`{"canary": ..., "examples": [...]}`) — the contamination guard everyone else skipped; we adopt this wrapper verbatim (D-013).
- Widest language coverage anywhere (29 langs, 13 scripts) with per-source license separation — meticulous data hygiene.
- Human translations, not MT — quality floor for low-resource languages.
**Did wrong / limits:**
- Translation-extension of *Western* datasets (CrossSum, FLORES, XQuAD) → translationese; measures translation transfer, not Indian knowledge or native competence.
- Data-only release: no eval harness, no leaderboard, no baseline scripts in repo — adoption friction.
- Static; no refresh story; CC-BY-NC-SA on CrossSum-IN fragments commercial use.
**IndiBench takes:** canary-per-file + license hygiene (build upon); native authoring instead of translation, and always shipping a runnable harness (improve).

### 4. Indic-Bias / FairI Tales (AI4Bharat, ACL 2025) — `indic-bias-master`
**What:** fairness/stereotype eval across 85 Indian identity groups (region/religion/caste/tribe); synthetic templates from a human taxonomy.
**Did right:**
- **Human-taxonomy-driven synthetic generation** — sociologist-defined identity/stereotype taxonomies expanded by LLMs into instances. This is the proof-of-concept for our S0→S1 pipeline: humans set the frame, models scale it.
- Clean `synth_data_gen/` vs `evaluations/` separation; multi-provider model adapter layer; OpenAI-batch-format pipelines — production-quality pipeline code.
- Three scoring paradigms matched to task types (ELO/Bradley-Terry, LLM-judge, association rate).
**Did wrong / limits:**
- No canary, no gating on the generated data.
- Committed `config.py` full of placeholder API-key fields — invites accidental secret commits.
- Fully-synthetic prompts without grounding documents → plausibility depends entirely on generator quality; no adversarial difficulty filter.
**IndiBench takes:** taxonomy-driven synthesis + pipeline/eval separation (build upon); grounding + adversarial filtering + canary (improve). Safety/bias itself stays their lane (pending owner call).

### 5. Indic-LLM (CognitiveLab) — `Indic-llm-main`
**Not a benchmark** (training toolkit; eval scripts are empty stubs, `docs/6_Eval.md` is 0 bytes). Audit lesson: shipping "evaluation" as a TODO is how credibility dies — IndiBench must never release a phase without its runnable eval. GPL-3 license would also be incompatible with our MIT code (reference-only).

### 6. Indic NLP Catalog — `indicnlp_catalog-master`
**Not a benchmark** (awesome-list). Audit lesson: the ecosystem's discovery layer is a README — useful as a source-document discovery index for our S0 corpus stage, and evidence that a maintained, runnable, versioned suite (not a link list) is the actual gap.

### 7–10. Non-Indian references in folder (context only)
- **HLE** (`hle-main`): did right — expert sourcing with incentives, tiny runnable eval, confidence+calibration reporting, multimodal schema, private held-out split, post-release corrections (HLE-Rolling). Did wrong — answer-key error rate (~18–29% in audited bio/chem slices) from weak source-grounding of keys; our S2 source-verification stage exists precisely because of this.
- **SWE-bench** (`SWE-bench-main`): did right — verifiable execution-based grading; τ²-Verified-style lesson: task/verification misalignment is the agentic failure mode. Out of scope otherwise (D-002).
- **lm-evaluation-harness**: the distribution standard for text tasks; we contribute a task config there even though Inspect AI is primary (D-012).
- **langfuse**: observability/eval-infra candidate for pipeline tracing; role still an open owner question.

---

## Part B — Trusted major benchmarks added for this audit (new clones, *-ref*)

### 11. IndicXTREME (AI4Bharat, ACL 2023) — `IndicBERT-IndicXTREME-ref`
**What:** 9-task NLU benchmark (COPA/QA/paraphrase/sentiment/NLI/NER/intent/retrieval), up to 18 Indic languages, paired with IndicCorp v2.
**Did right:** benchmark + corpus + model released as one reproducible unit; manual translation of test sets (quality floor); broadest task-type diversity of the AI4Bharat line.
**Did wrong / limits:** classic NLU tasks are pre-LLM framing (classification heads, not generation/reasoning); several tasks are translations of Western datasets (COPA, XNLI) → same translationese ceiling; saturated by modern LLMs.
**IndiBench takes:** release-everything-together reproducibility (build upon); task framing must be generative/reasoning-native (improve).

### 12. IndicSUPERB + Kathbath (AI4Bharat, 2022) — `IndicSUPERB-ref`
**What:** 6 speech tasks, 12 languages; Kathbath = 1,684 hours labelled speech, 1,218 speakers, clean + noisy splits.
**Did right:** dual clean/noisy test splits and known/unknown-speaker splits — exactly the acoustic-diversity thinking goals.md demands; speaker/gender metadata in filenames; massive scale.
**Did wrong / limits:** read/elicited speech, not spontaneous; ASR-era tasks (no spoken reasoning, no TTS eval, no speech-to-speech); 2022-frozen — no frontier-model results; downloads on a single object store (fragility).
**IndiBench takes:** clean/noisy + known/unknown split design for Phase 2 (build upon); spontaneous speech, TTS, and spoken-interaction evaluation (improve — the open niche our research confirmed).

### 13. MASSIVE (Amazon, 2022) — `massive-ref`
**What:** 1M+ utterances, 52 languages (7 Indic), intent + slot annotation, parallel; the base for MASSIVE-Agents (2025).
**Did right:** true parallelism across languages enables exact cross-lingual comparison; professional localization; leaderboard + shared task drove adoption.
**Did wrong / limits:** voice-assistant single-turn NLU — not conversation, not environments; Indic languages a minority slice; localization ≠ localization of *content* (utterances are Western-assistant scenarios translated).
**IndiBench takes:** parallel-across-languages design where possible (build upon); Indian-native scenarios rather than localized Western ones (improve — this is Ticket-Bench's "regionalization" lesson too).

### 14. COMI-LINGUA (IIT Gandhinagar, EMNLP 2025) — `COMI-LINGUA-ref` (repo is a license stub; data on HF `LingoIITGN/COMI-LINGUA`)
**What:** 125k+ expert-annotated Hinglish instances, 5 tasks, both Devanagari and Roman scripts.
**Did right:** largest modern code-mix resource; dual-script coverage (romanized vs native — the Script Gap paper showed this matters); expert annotation at scale.
**Did wrong / limits:** classic NLP tasks (LID/POS/NER/MT) — no reasoning, no generation quality, no frontier positioning; GitHub repo contains no code (HF-only artifact) — weak reproducibility surface.
**IndiBench takes:** dual-script code-mix design (build upon); reasoning-level code-mix items, which nobody has (improve — frontier Hinglish/Tanglish is ours to claim, D-008/D-019).

---

## Part C — Audited from public artifacts (no clone available)

### 15. IndQA (OpenAI, Nov 2025)
**Did right:** first frontier-positioned India benchmark (GPT-5 ≈35%); 261 paid domain experts; rubric-based grading; adversarial filtering at creation; Hinglish as first-class.
**Did wrong / limits:** **closed data, closed grading** — nobody can run it themselves or audit keys; filtered only against OpenAI models (lab-biased difficulty); culture/humanities-heavy (no STEM/professional depth); no refresh mechanism announced.
**IndiBench takes:** difficulty bar + expert-rubric idea (build upon via S4); openness, cross-lab filtering, domain breadth, renewability (improve — our entire D-019 identity).

### 16. ParamBench (BharatGen, Aug 2025; HF `bharatgenai/ParamBench`)
**Did right:** graduate-entrance difficulty (best model 56.4%) — hardest open Indian set; diverse question formats (assertion-reason, matching, sequencing) that stress reasoning beyond recall.
**Did wrong / limits:** Hindi-only; exam-harvested (contamination); MCQ-only; no harness repo.
**IndiBench takes:** hard question *formats* for our generator prompts (build upon); multilingual + contamination-safe (improve).

### 17. DRISHTIKON (EMNLP 2025; no public repo found)
**Did right:** 64k text-image pairs, 15 languages, all states/UTs — proves culturally-grounded multimodal data can be built at scale; findings confirm VLMs fail on low-resource-language cultural reasoning (supports the owner's multimodal thesis directly).
**Did wrong / limits:** no discoverable code/repo release at audit time (paper-only reproducibility); MCQ framing; CC-BY-SA-4.0 share-alike friction.
**IndiBench takes:** validation that Phase 3's niche is real and under-served openly; we must out-execute on release completeness.

### 18. Global-MMLU / IndicMMLU-Pro / MMLU-ProX / hle-multilingual (2024–26)
**Did right:** cheap broad multilingual coverage; Global-MMLU at least tags culture-sensitive vs culture-agnostic items.
**Did wrong / limits:** all are translations of Western tests — translationese, contaminated bases, zero Indian grounding. hle-multilingual (machine-translated HLE) proves the demand for a frontier-hard non-English benchmark AND the absence of a native one.
**IndiBench takes:** the anti-pattern. Native authoring is non-negotiable (already locked, D-009/D-010).

### 19. Voice of India (Josh Talks + AI4Bharat, Feb 2026)
**Did right:** national-scale ASR eval (15 langs, 35k+ speakers) showing global models at 20–30% WER — evidence Indian speech is unsolved.
**Did wrong / limits:** ASR-only — no TTS, no spoken reasoning, no interaction.
**IndiBench takes:** partnership/data candidate for Phase 2; our differentiation = the interactive/generative speech layer above ASR.

### 20. Indic LLM-Arena (AI4Bharat, Nov 2025)
**Did right:** human-preference modality for Indic + code-mixed prompts; open model onboarding.
**Did wrong / limits:** preference ≠ correctness (popularity contest can't anchor factuality); vote volume for low-resource languages will be thin; Phase 3 (agentic) still unshipped.
**IndiBench takes:** complementary partner (D-018), not a model to copy; static verifiable scoring remains our core.

---

## Part D — Synthesis

### Build upon (what the ecosystem got right)
1. **Packaging:** MILU/BhashaBench's one-command harness tasks; IndicXTREME's release-everything reproducibility. → Every IndiBench phase ships data + harness + baselines + paper together.
2. **Contamination defense:** IndicGenBench's canary-per-file. → Adopted (D-013), extended with private split + renewability.
3. **Synthesis pipeline:** Indic-Bias's taxonomy-driven generation with clean pipeline/eval separation. → Our S0–S5 pipeline is this, plus grounding and adversarial filtering.
4. **Domain authenticity:** BhashaBench's professional-domain axis; ParamBench's hard question formats. → Feed domain taxonomy and generator prompt design.
5. **Speech test design:** IndicSUPERB's clean/noisy + known/unknown splits. → Phase 2 skeleton.
6. **Parallelism:** MASSIVE's cross-language parallel items. → Use for the code-mixed and cross-language comparability slices.
7. **Difficulty bar + expert rubric:** IndQA (and HLE). → Our S3/S4 stages.

### Improve (what everyone got wrong — IndiBench's reason to exist)
1. **Contamination-by-construction** (MILU, BhashaBench, ParamBench harvest public exams) → synthetic grounded generation; exams as syllabi only (D-017).
2. **Saturation on arrival** (every open Indian benchmark: 56–77% for frontier models) → cross-lab adversarial filter keeps only what models fail (D-010).
3. **Translationese** (IndicGenBench, IndicMMLU-Pro, Global-MMLU, hle-multilingual) → native authoring in-script, never translation (D-009).
4. **Closedness** (IndQA closed data; DRISHTIKON no repo; COMI-LINGUA no code) → open data + harness + pipeline, inspect_evals + lm-eval registration (D-019).
5. **Staleness** (everything is a frozen artifact) → renewable refresh waves with versioning (D-013).
6. **Modality gaps** (text-MCQ monoculture; ASR-only speech; no TTS/spoken-interaction; no agentic anything; near-zero image-generation eval) → the four-phase suite (D-020) + THESIS.md.
7. **English/Hindi gravity** (BhashaBench 2 langs, ParamBench 1) → 10–12 languages at parity in v1, 22 as end-goal (D-008/D-017).
8. **Answer-key fragility** (HLE's audit crisis) → source-grounded keys + verification stage + bug bounty + rolling corrections.

### "The only benchmark somebody needs in India" — what it concretely means
One suite, four phases, one schema family, one harness, one leaderboard:
frontier text (Phase 1), speech in/out (Phase 2), vision in/out (Phase 3),
agents on Indian rails (Phase 4) — each open, contamination-defended,
renewable, and hard enough to matter. Broad-coverage MCQ (MILU's lane) stays
out of scope (D-003/D-007): "only benchmark you need" = every *use case*
covered at frontier difficulty, not every difficulty level duplicated.
