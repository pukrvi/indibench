# Research: Indic Benchmark Landscape — Is the Niche Open? (as of 2026-07)

Date: 2026-07-12 · Work interleave 1 (after question Batch 2) · Web research, sources cited inline.

## Verdict

- **Track 1 (frontier-hard Indic knowledge): partially occupied.** OpenAI's
  **IndQA** (Nov 2025) planted the "HLE-for-India" flag: 2,278 questions, 12
  language tracks incl. Hinglish, 10 cultural domains, 261 Indian experts,
  adversarially filtered against OpenAI models (GPT-5 Thinking High ≈ 34.9%).
  BUT it is closed-data (no HF/GitHub release), graded by OpenAI, culture/
  humanities-only, filtered only against OpenAI's own models.
  (https://openai.com/index/introducing-indqa/)
- **Track 2 (Indic agentic): wide open.** No UPI/IRCTC/gov-portal environment
  benchmark exists in any Indic language. Closest: Amazon MASSIVE-Agents
  (single-turn function calling, 52 langs, top model 34% — no environments, no
  Indian services); Ticket-Bench (regionalized agent template, zero Indic).

## Differentiators IndiBench can own (Track 1 vs IndQA)

1. Fully open data + harness (IndQA is closed).
2. Adversarial filtering against ALL frontier labs' models, not just OpenAI's.
3. Document-grounded synthetic generation at scale (vs 2,278 hand-written).
4. Hard STEM/professional/exam-difficulty content (IndQA is culture-only).
5. Tanglish + more code-mixed pairs (IndQA covers Hinglish only). Frontier-hard
   Tanglish is fully unclaimed.

## Landscape table (none of the Indian-built sets are frontier-hard)

| Benchmark | Date | Scope | Why it doesn't occupy our niche |
|---|---|---|---|
| IndQA (OpenAI) | 2025-11 | 2,278 Q, 12 langs, culture | Closed data, OpenAI-only filtering, no STEM |
| MILU (AI4Bharat) | 2024-11 | ~80k MCQ, 11 langs | GPT-4o ~72-74% — saturating |
| BhashaBench (BharatGen) | 2025-10 | 74k QA, En+Hi, 4 domains | GPT-4o 60-77%, bilingual only |
| ParamBench | 2025-08 | 17k+ grad-exam Q, Hindi only | Hindi-only MCQ, mid-hard |
| IndicParam | 2025-12 | 13k+ Q, 11 low-resource langs | Low-resource focus, not frontier positioning |
| IndicMMLU-Pro / MMLU-ProX / Global-MMLU | 2025 | translated MMLU variants | Translationese + contamination |
| hle-multilingual (ellamind) | 2026 | machine-translated HLE | Pure translation — proves no native Indic HLE exists |
| MASSIVE-Agents (Amazon) | 2025 EMNLP | 47k function calls, 52 langs | Single-turn, no environments, no Indian services |
| Ticket-Bench | 2025-09 | agent env template, 6 langs | Zero Indic; validates regionalization thesis |
| IndicDB | 2026-04 | text-to-SQL, 7 Indic langs | Narrow task |
| COMI-LINGUA (IIT-GN) | 2025 | 125k Hinglish annotations | Classic NLP tasks, not reasoning |
| Voice of India (Josh Talks + AI4Bharat) | 2026-02 | ASR, 15 langs | Speech only; relevant if speech track added |
| Indic LLM-Arena (AI4Bharat) | 2025-11 | human-preference arena, Indic + code-mixed | Complementary modality; Phase 3 = agentic (watch/partner) |

## Most-cited gaps in Indic LLM evaluation (2025-26 surveys)

(a) translationese ≠ native competence; (b) exam-scrape contamination;
(c) saturation — nothing Indian is frontier-hard; (d) shallow cultural
grounding; (e) romanized/code-mixed text ignored; (f) near-zero agentic
evaluation in Indic languages; (g) safety drift across languages.
IndiBench's tracks map onto (c)+(a) and (f).

## Ecosystem notes

- **IndiaAI/AIKosh** hosts benchmark datasets (MILU is on it) — distribution channel.
- **New Delhi Frontier AI Commitments** (Feb 2026 summit): labs committed to
  supporting under-represented-language benchmarks — partnership/funding hook.
- **Sarvam/Krutrim** are prospective users (Indian model builders need
  independent hard evals), not competitors.
- **Watch-item:** AI4Bharat/BharatGen are the likeliest next entrants into
  frontier-difficulty or agentic Indic benchmarks — and also our most natural
  partners. Timing matters either way.
