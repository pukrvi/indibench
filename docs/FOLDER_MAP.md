# Folder Map — /IndiBench

Last updated: 2026-07-13 (alignment phase). Update whenever files/folders change.

Git: this folder is the working copy of https://github.com/pukrvi/indibench
(MIT). `benchmarks/` and `.claude/` are gitignored. Workflow: feature branches
→ PR → sub-agent review → merge (D-014).

```
IndiBench/
├── CLAUDE.md                  # Project guide for Claude + humans; read first
├── README.md                  # Public project README (idea, thesis, phases, pipeline, status)
├── LICENSE                    # MIT (code)
├── CONTRIBUTING.md            # Contribution policy (D-037): errors + sources yes, questions no
├── pyproject.toml             # Python package `indibench`
├── .gitignore                 # excludes benchmarks/, .claude/, .venv/, .DS_Store
├── .github/ISSUE_TEMPLATE/    # question_error_report.yml (D-037 bug-report channel)
├── goals.md                   # Owner's goals document (Input 002) — verbatim owner input
├── LMBench_References.md      # Owner's curated reference list of benchmark repos (original input)
├── src/indibench/             # Package: schema.py (D-030/031/038), canary.py (D-013)
│   └── pipeline/              # S0–S5 stages; S3 survival/S4 gates/S5 release implemented,
│                              #   LLM plumbing (S0-S2, S3 panel calls) pending
├── evals/
│   ├── inspect/indibench_text.py   # Inspect AI task (D-012; inspect_evals/hle pattern)
│   └── standalone/predict.py, judge.py  # HLE-style zero-framework local eval (D-015)
├── tests/                     # Unit tests for pure pipeline logic (6 passing)
├── data/                      # Public releases will land here (README only for now)
├── docs/
│   ├── USER_INPUTS.md         # VERBATIM record of all owner inputs (source of truth for intent)
│   ├── DECISIONS.md           # Alignment-loop decisions log (every Q, every A, D-### decisions)
│   ├── THESIS.md              # The India-is-multimodal thesis (D-024, from Input 003)
│   ├── FOLDER_MAP.md          # This file
│   ├── PROJECT_MAP.md         # What we're building: phases, workstream status
│   ├── design/
│   │   └── phase1-indibench-text.md         # Phase 1 design doc (DRAFT — open items feed Batch 5+)
│   └── research/              # Dated research reports from work interleaves
│       ├── 2026-07-12-indic-landscape.md    # Competitive landscape; IndQA analysis; niche verdict
│       ├── 2026-07-12-harness-and-arena.md  # Inspect AI / LM Arena / renewable benchmarks / tau2
│       └── 2026-07-13-benchmark-audit.md    # 20-benchmark audit (Input 003): right/wrong + synthesis
└── benchmarks/                # REFERENCE REPOS (gitignored) — read-only study material, not our code
    ├── BhashaBench-main/          # BharatGen: ~74k domain MCQs (agri/finance/legal/ayur), En+Hi.
    │                              #   lm-eval-harness fork. Pattern: _default_template_yaml + per-lang YAMLs.
    ├── MILU-master/               # AI4Bharat: ~80k exam MCQs, 11 langs. Same harness pattern as BhashaBench.
    │                              #   The "MMLU of India" — what we must NOT duplicate.
    ├── indic-gen-bench-main/      # Google: generation tasks, 29 langs. COPY: canary-GUID-per-file JSON
    │                              #   wrapper {canary, examples}; per-source license separation.
    ├── indic-bias-master/         # AI4Bharat: bias/fairness across 85 Indian identity groups. COPY:
    │                              #   synth_data_gen/ vs evaluations/ separation; taxonomy-driven synthesis.
    ├── Indic-llm-main/            # CognitiveLab training toolkit (not a benchmark; eval is a stub). Low value here.
    ├── indicnlp_catalog-master/   # Awesome-list of Indic NLP resources. Use as discovery index for source data.
    ├── hle-main/                  # Humanity's Last Exam. COPY: schema (id/question/image/answer), LLM-judge
    │                              #   with structured output, accuracy + calibration error, tiny eval codebase.
    ├── SWE-bench-main/            # Reference for how a frontier benchmark defines/validates tasks.
    │                              #   Coding benchmarks are OUT OF SCOPE (D-002) — structural study only.
    ├── lm-evaluation-harness-main/# EleutherAI harness. Target for contributing our knowledge-track task config.
    ├── langfuse-main/             # LLM observability/eval platform. Candidate infra for tracing pipeline runs,
    │                              #   storing eval scores/datasets. Role not yet decided (ask owner).
    │   # ---- Added 2026-07-13 for the Input 003 audit (shallow clones): ----
    ├── IndicBERT-IndicXTREME-ref/ # AI4Bharat IndicXTREME: 9-task NLU benchmark, up to 18 langs (ACL 2023)
    ├── IndicSUPERB-ref/           # AI4Bharat speech benchmark: 6 SLU tasks, 12 langs; Kathbath 1,684h.
    │                              #   COPY: clean/noisy + known/unknown-speaker split design (Phase 2)
    ├── massive-ref/               # Amazon MASSIVE: 1M+ utterances, 52 langs parallel, intent+slots.
    │                              #   COPY: cross-language parallel item design
    └── COMI-LINGUA-ref/           # IIT-GN Hinglish benchmark — repo is a license stub; data on HF
                                   #   (LingoIITGN/COMI-LINGUA). Dual-script code-mix reference.
```

## Reproducing `benchmarks/` (gitignored — clone these to study them)

```
git clone https://github.com/BharatGen-IITB-TIH/BhashaBench          benchmarks/BhashaBench-main
git clone https://github.com/AI4Bharat/MILU                          benchmarks/MILU-master
git clone https://github.com/google-research-datasets/indic-gen-bench benchmarks/indic-gen-bench-main
git clone https://github.com/AI4Bharat/indic-bias                    benchmarks/indic-bias-master
git clone https://github.com/adithya-s-k/Indic-llm                   benchmarks/Indic-llm-main
git clone https://github.com/AI4Bharat/indicnlp_catalog              benchmarks/indicnlp_catalog-master
git clone https://github.com/centerforaisafety/hle                   benchmarks/hle-main
git clone https://github.com/swe-bench/SWE-bench                     benchmarks/SWE-bench-main
git clone https://github.com/EleutherAI/lm-evaluation-harness        benchmarks/lm-evaluation-harness-main
git clone https://github.com/langfuse/langfuse                       benchmarks/langfuse-main
# Audit additions (2026-07-13):
git clone --depth 1 https://github.com/AI4Bharat/IndicBERT           benchmarks/IndicBERT-IndicXTREME-ref
git clone --depth 1 https://github.com/AI4Bharat/IndicSUPERB         benchmarks/IndicSUPERB-ref
git clone --depth 1 https://github.com/alexa/massive                 benchmarks/massive-ref
git clone --depth 1 https://github.com/lingo-iitgn/COMI-LINGUA       benchmarks/COMI-LINGUA-ref
```

## Planned additions (once alignment closes)

- Our own benchmark code + data pipeline (structure TBD after Batch 3+ —
  likely: `src/` or a named package, `data/` with public/private splits,
  `pipeline/` for synthetic generation, `evals/` for Inspect AI tasks).
