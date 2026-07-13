"""The S0–S5 synthetic generation pipeline (design doc §3).

Stage status (build phase, July 2026):
- s1_author, s2_verify, s3_filter: implemented — need provider API keys (D-042)
- s3_filter.survives_filter, s4_spotcheck, s5_release: pure logic, tested
- s0_corpus: interface defined; corpus building is the open milestone
Run order: S0 → S1 → S2 → S3 → S4 (human, tooling-assisted) → S5.

The v0-seed candidate pool (D-041) enters the pipeline at S2: it was
authored in-session at S1 level and awaits verification/filtering.
"""
