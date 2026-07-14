# Implementation Audit — Pre-key Review

Date: 2026-07-13  
Scope: the code and v0-seed produced before real provider API keys are added.

## Verdict

**The repository is ready for a controlled S2/S3 API filtering run, but it is
not a released benchmark and must not be described as one.** The 240-item
pool is an unfiltered, source-claim-only seed; the Phase-1 release target is
about 2,500 filtered public items plus a private split.

The prior implementation correctly made candidates visibly unfiltered and
provided a working offline harness. This audit found that its release command
could nevertheless write an official-looking dataset without the two
non-automatable trust requirements: verified S0 sources and S4 expert audits.
That gap is closed in this audit branch.

## Verification performed

| Surface | Result |
|---|---|
| Candidate structure | 240/240 validate; 13 file codes correctly represent 12 tracks because code-mixed contains `hi-Latn` and `ta-Latn` variants. |
| Canary | Candidate wrappers validate; release schema/harness validate canaries. |
| Pure pipeline logic | S3 threshold, S4 sample logic, deterministic S5 split, promotion and release write paths covered by tests. |
| Offline orchestration | `--mock` exercises S2/S3-shaped control flow, results caching, promotion and S5; it does not establish benchmark quality. |
| Inspect / standalone evaluation | Loader and mocked grading paths run; live provider compatibility remains keys-day validation. |
| Source grounding | **Not present for v0-seed.** `grounding_note` is a claimed basis, not a retrieved source record. |
| Human review | **Not present for v0-seed.** No S4 expert verdicts exist. |

## Defects found and corrected

1. **Release without source provenance:** `promote()` used
   `source_type="parametric-draft"`, allowing claimed grounding notes to be
   coarsened into public provenance. It now requires a matching registered S0
   `SourceDocument`, whose content hash is what ships publicly.
2. **Release without expert evidence:** S4 existed only as a helper. The
   release command now requires an S0 manifest and S4 audit-verdicts file for
   real release promotion. It enforces one passing audit per language/domain
   cell at minimum (ceil 10%), and passing audits for every safety-tagged item.
3. **Mock output could resemble a release:** mock runs now refuse to write
   files unless the explicit test-only `--allow-mock-release` flag is given.
4. **S0 was a build stub:** it is now a manifest validator with explicit
   license allow-list and content-hash requirements. Discovery remains a
   documented research workflow rather than an uncontrolled scraper.
5. **Release writes were non-atomic:** S5 now writes via a temporary file and
   atomic rename.

## Remaining blockers to a real release

These are project work, not implementation bugs:

- Build a license-reviewed S0 corpus and link every candidate to a verified
  source document. The current v0 seed must be re-authored or re-grounded.
- Run S2 with source excerpts, then S3 against the pinned cross-lab panel.
- Recruit native-language/domain reviewers and record S4 verdicts; all safety
  candidates require review.
- Scale from 240 candidates to enough source-grounded candidates that roughly
  2,500 survive the panel; 240 is a pilot seed, not a v1 dataset.
- Validate real provider endpoints, model pins, pricing/rate limits and
  judge agreement with the supplied API keys.

## Correct operational status

| Claim | Status |
|---|---|
| Pipeline code can be exercised without keys | Yes |
| Candidate pool can undergo S2/S3 review when keys are supplied | Yes |
| v0-seed is source-grounded / expert-audited | No |
| An official dataset can be produced from v0-seed today | No — intentionally prevented by release gates |
| Phase 1 v1 benchmark is complete | No — target remains ~2,500 filtered questions |
