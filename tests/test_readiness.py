"""Readiness tests: everything that must work BEFORE API keys are attached.

Covers provider error paths (no keys), judging helpers, candidate→Item
promotion, and an end-to-end offline integration: candidate files → mock
filter → promote → split → versioned release → eval-loader roundtrip.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from indibench import providers
from indibench.canary import is_valid_canary
from indibench.judging import mcq_reference, normalize, render_mcq
from indibench.pipeline.promote import promote
from indibench.pipeline.release_gate import ReleaseEvidenceError, require_release_evidence
from indibench.pipeline.s0_corpus import SourceDocument
from indibench.pipeline.s4_spotcheck import AuditVerdict
from indibench.pipeline.s3_filter import PanelResult
from indibench.pipeline.s5_release import split_public_private, write_release
from indibench.schema import CandidateFile, DatasetFile

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data" / "candidates" / "v0-seed"


def _panel(fails: int) -> list[PanelResult]:
    return [PanelResult(model_id=f"m{i}", answered_correctly=(i >= fails)) for i in range(4)]


def _source_for(draft) -> SourceDocument:
    return SourceDocument(
        doc_id=f"src-{draft.id}", language=draft.language, domain=draft.domain,
        source_type="gazette", license="GODL-India",
        provenance_url="https://example.gov.in/source",
        content_sha256="a" * 64,
    )


def test_providers_fail_loudly_without_keys(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        providers.complete("openai/gpt-5", "s", "u")
    with pytest.raises(ValueError, match="unknown provider"):
        providers.complete("nosuch/model", "s", "u")
    with pytest.raises(ValueError, match="provider"):
        providers.complete("modelwithoutslash", "s", "u")


def test_judging_helpers():
    assert normalize("  Bharat Ratna. ") == normalize("bharat-ratna")
    assert normalize("") == ""
    q = render_mcq("Pick one", ["x", "y"])
    assert "A. x" in q and "B. y" in q
    assert render_mcq("Pick one", None) == "Pick one"
    assert mcq_reference("B", ["x", "y"]) == "B (y)"
    assert mcq_reference("free text", None) == "free text"


def test_all_seed_files_valid_and_canaried():
    files = sorted(SEED_DIR.glob("*.json"))
    assert len(files) == 13  # 12 tracks; code-mixed = hi-Latn + ta-Latn
    total = 0
    for path in files:
        cf = CandidateFile.model_validate_json(path.read_text(encoding="utf-8"))
        assert is_valid_canary(cf.canary), path.name
        assert cf.status == "candidates-unfiltered"
        assert all(d.id for d in cf.examples)
        total += len(cf.examples)
    assert total == 240


def test_promote_end_to_end_offline(tmp_path):
    """Candidate files → survival → promote → split → release → loader roundtrip."""
    drafts = []
    for path in sorted(SEED_DIR.glob("*.json")):
        drafts.extend(CandidateFile.model_validate_json(path.read_text(encoding="utf-8")).examples)
    # simulate: half the pool survives (2 of 4 panel models fail)
    promoted_drafts = drafts[::2]
    sources = {}
    for draft in promoted_drafts:
        source = _source_for(draft)
        draft.source_document_id = source.doc_id
        sources[source.doc_id] = source
    survivors = [promote(d, _panel(fails=2), "vTEST", ["anthropic/j1", "google/j2"],
                         source=sources[d.source_document_id]) for d in promoted_drafts]
    assert all(item.id.startswith("ibt-") for item in survivors)
    assert all(len(item.difficulty_evidence.models_failed) == 2 for item in survivors)
    # Provenance must be the registered source hash, never grounding-note text.
    for draft, item in zip(promoted_drafts, survivors):
        assert item.provenance.source_ref == sources[draft.source_document_id].content_sha256[:12]

    public, private = split_public_private(survivors, seed=7)
    written = write_release(public, tmp_path, "vTEST",
                            (ROOT / "data" / "CANARY_GUID").read_text().strip())
    assert written
    # every written release file must round-trip through the release schema + canary check
    for path in written:
        df = DatasetFile.model_validate_json(path.read_text(encoding="utf-8"))
        assert is_valid_canary(df.canary)
        assert df.examples


def test_promote_refuses_non_survivors():
    drafts = CandidateFile.model_validate_json(
        next(iter(sorted(SEED_DIR.glob("*.json")))).read_text(encoding="utf-8")).examples
    source = _source_for(drafts[0])
    drafts[0].source_document_id = source.doc_id
    with pytest.raises(ValueError, match="did not survive"):
        promote(drafts[0], _panel(fails=1), "vTEST", ["j1", "j2"], source=source)


def test_v0_seed_cannot_pass_official_release_gate():
    """Claims in grounding_note are not S0 provenance or S4 evidence."""
    draft = CandidateFile.model_validate_json(
        next(iter(sorted(SEED_DIR.glob("*.json")))).read_text(encoding="utf-8")
    ).examples[0]
    with pytest.raises(ReleaseEvidenceError, match="S0 source evidence missing"):
        require_release_evidence([draft], {}, {})


def test_release_gate_accepts_matching_source_and_audit():
    draft = CandidateFile.model_validate_json(
        next(iter(sorted(SEED_DIR.glob("*.json")))).read_text(encoding="utf-8")
    ).examples[0]
    source = _source_for(draft)
    draft.source_document_id = source.doc_id
    verdict = AuditVerdict(
        item_id=draft.id, expert_id="reviewer-1", key_correct=True,
        question_well_formed=True,
    )
    require_release_evidence([draft], {source.doc_id: source}, {draft.id: verdict})


def test_standalone_judge_metrics():
    """Calibration math in the standalone judge (HLE method)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "judge", ROOT / "evals" / "standalone" / "judge.py")
    judge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(judge)
    # perfectly calibrated: 50% confidence, 50% accuracy -> error 0
    assert judge.calibration_error_rms([50.0, 50.0], [True, False]) == pytest.approx(0.0)
    # perfectly miscalibrated: 100% confident, always wrong -> error 100
    assert judge.calibration_error_rms([100.0] * 4, [False] * 4) == pytest.approx(100.0)
    assert judge.calibration_error_rms([], []) == 0.0


def test_run_filter_mock_dry_run(tmp_path):
    """The orchestration script must run end-to-end offline in --mock mode."""
    results = tmp_path / "results.jsonl"
    base = [sys.executable, str(ROOT / "scripts" / "run_filter.py"),
            "--mock", "--skip-s2", "--results", str(results)]
    proc = subprocess.run(
        base + ["--limit", "30",
                "--promote-to", str(tmp_path / "rel"), "--version", "vTEST",
                "--force-partial-promotion", "--allow-mock-release"],
        capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    assert "MOCK MODE" in proc.stdout and "Yield report" in proc.stdout
    lines = [json.loads(line) for line in results.read_text().splitlines()]
    assert len(lines) == 30
    assert all("survived" in r for r in lines)
    # promotion must actually write release files (public AND private dirs)
    assert list((tmp_path / "rel" / "public" / "vTEST").glob("*.json"))
    assert list((tmp_path / "rel" / "private" / "vTEST").glob("*.json"))
    # resumability: second run must skip everything already processed
    proc2 = subprocess.run(base + ["--limit", "30"],
                           capture_output=True, text=True, timeout=180)
    assert "30 already processed" in proc2.stdout
    # corruption tolerance: truncated final line is dropped, not fatal
    with results.open("a") as f:
        f.write('{"id": "ibc-truncat')
    proc3 = subprocess.run(base + ["--limit", "2"],
                           capture_output=True, text=True, timeout=180)
    assert proc3.returncode == 0, proc3.stderr
    assert "truncated final line" in proc3.stdout
    # guardrails: promotion without full processing refuses; flags must pair
    proc4 = subprocess.run(
        base + ["--limit", "1", "--promote-to", str(tmp_path / "rel2"), "--version", "vX",
                "--allow-mock-release"],
        capture_output=True, text=True, timeout=180)
    assert proc4.returncode != 0 and "REFUSING to promote" in (proc4.stdout + proc4.stderr)
    proc5 = subprocess.run(base + ["--promote-to", str(tmp_path / "rel3")],
                           capture_output=True, text=True, timeout=180)
    assert proc5.returncode != 0
    # config mismatch: different panel pin against same results file must error
    proc6 = subprocess.run(base + ["--limit", "1", "--tiebreak", "openai/other-model"],
                           capture_output=True, text=True, timeout=180)
    assert proc6.returncode != 0 and "run config" in (proc6.stdout + proc6.stderr)
