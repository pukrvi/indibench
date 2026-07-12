# The IndiBench Thesis: India Is a Multimodal Evaluation Problem

Adopted 2026-07-13 from owner Input 003 (see `docs/USER_INPUTS.md` for the
verbatim statement). This document is the reasoned form of that thesis; it
governs why the suite is four phases rather than a text benchmark with
extensions.

## The claim

For India, text-only evaluation structurally under-measures what matters.
Beyond the usual LLM benchmarks, an AI system serving India must be evaluated
on:

1. **Understanding India visually** — images of Indian life (festivals,
   attire, architecture, food, signage, documents, charts in Indian scripts)
   interpreted correctly, region by region.
2. **Producing India correctly** — generated images (and other outputs) that
   are contextually and **historically accurate** for India: the right
   temple architecture for the right state, the right drape of a sari for the
   right region, the right script on a shopfront — not a generic "exotic
   India" collage.
3. **Language understanding** — native-script and code-mixed competence at
   frontier difficulty, not translationese.
4. **Voice-to-text and voice-to-speech** — speech is the primary interface
   for hundreds of millions of Indian users; STT and TTS quality across
   dialects, districts, and real acoustic conditions is core capability, not
   an accessory.

## Why this is true (evidence, 2025–26)

- **Voice-first reality:** national-scale testing (Voice of India, Feb 2026)
  still measures 20–30% WER for global ASR on Indian languages — speech is
  both critical and unsolved.
- **Vision models fail Indian culture:** DRISHTIKON (EMNLP 2025, 64k
  text-image pairs across all states/UTs) documents systematic VLM failures on
  culturally grounded reasoning, worst in low-resource languages;
  HinTel-AlignBench shows frontier VQA drops measurably in Hindi/Telugu.
- **Image generation misrepresents India:** cultural- and historical-accuracy
  evaluation of image *output* for India barely exists; errors are visible to
  any Indian user and corrosive to trust (and no benchmark measures them
  systematically — see audit §17–18).
- **Text-only Indian benchmarks saturated** at 56–77% for frontier models
  while the multimodal/speech/agentic surface went unmeasured (audit Part D).

## What it commits IndiBench to

- The four-phase suite (D-020: text > speech > vision > agent) is the
  product of this thesis, not a nice-to-have roadmap.
- Phase 2 evaluates **both directions** of voice (STT and TTS/spoken
  interaction), with dialect and acoustic diversity as first-class axes.
- Phase 3 evaluates **both directions** of vision: understanding India in
  images AND generating India correctly (historical/cultural accuracy of
  image output). *(Image-output evaluation methodology is an open design
  question — flagged for the alignment loop.)*
- Historical accuracy is a scored dimension wherever it applies (text claims,
  image content, spoken answers).
- Phase 1's schema reserves the `image` field from day one so the suite
  converges rather than fragments.
