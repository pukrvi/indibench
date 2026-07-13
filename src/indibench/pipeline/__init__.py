"""The S0–S5 synthetic generation pipeline (design doc §3).

Stage status (build phase, July 2026):
- s3_filter: survival logic implemented (pure function, testable)
- s5_release: canary injection + splitting implemented
- s0_corpus, s1_author, s2_verify: interfaces defined, LLM calls TODO
Run order: S0 → S1 → S2 → S3 → S4 (human, tooling-assisted) → S5.
"""
