# Contributing to IndiBench

Thanks for wanting to help make AI measurably better for India. The
contribution policy below is deliberate (decisions D-014/D-037 in
[docs/DECISIONS.md](docs/DECISIONS.md)) — please read it before opening a PR.

## What we welcome

1. **Error reports (most valuable!).** Wrong answer key, ambiguous question,
   bad transliteration, mislabeled language/domain — open an issue using the
   *Question error report* template. Verified reporters are credited in
   release notes and paper acknowledgments. Corrections ship in
   IndiBench-Rolling between releases.
2. **Grounding sources.** Hard, well-licensed Indian documents in any
   scheduled language: regional-language textbooks, state gazettes, case law,
   government manuals. Open an issue with the source, its license, and why
   it's hard. Government/public-domain (GODL-India) material preferred.
3. **Pipeline and harness improvements.** Code PRs to `src/indibench/` and
   `evals/` are welcome.
4. **Domain expertise.** Volunteer experts who spot-check items (especially
   beyond Hindi/English) earn co-authorship consideration on the paper.
   Open an issue introducing yourself.

## What we don't accept

- **Directly contributed benchmark questions.** IndiBench's methodology is
  synthetic generation grounded in source documents, adversarially filtered
  across labs. Hand-written questions — however good — can't carry the same
  contamination and difficulty guarantees, so the funnel stays closed by
  design. Contribute sources instead; the pipeline is open, run it.

## Development workflow

- Never commit directly to `main`. Feature branch → PR → review → squash-merge.
- Code license MIT; data CC BY 4.0. Don't commit anything from `benchmarks/`
  (reference clones, gitignored) or any private-split material.
- Keep the living docs current: any change of scope touches
  `docs/DECISIONS.md`, `docs/PROJECT_MAP.md`, and `docs/FOLDER_MAP.md`.
