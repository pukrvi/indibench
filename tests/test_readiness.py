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
from indibench.pipeline.s3_filter import PanelResult
from indibench.pipeline.s5_release import split_public_private, write_release
from indibench.schema import CandidateFile, DatasetFile

ROOT = Path(__file__).resolve().parent.parent
SEED_DIR = ROOT / "data" / "candidates" / "v0-seed"


def _panel(fails: int) -> list[PanelResult]:
    return [PanelResult(model_id=f"m{i}", answered_correctly=(i >= fails)) for i in range(4)]


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
    survivors = [promote(d, _panel(fails=2), "vTEST", ["anthropic/j1", "google/j2"])
                 for d in drafts[::2]]
    assert all(item.id.startswith("ibt-") for item in survivors)
    assert all(len(item.difficulty_evidence.models_failed) == 2 for item in survivors)
    # provenance must NOT leak the grounding note
    notes = {d.grounding_note for d in drafts}
    assert all(item.provenance.source_ref not in notes for item in survivors)

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
    with pytest.raises(ValueError, match="did not survive"):
        promote(drafts[0], _panel(fails=1), "vTEST", ["j1", "j2"])


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
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_filter.py"),
         "--mock", "--skip-s2", "--limit", "30",
         "--results", str(results),
         "--promote-to", str(tmp_path / "rel"), "--version", "vTEST"],
        capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "MOCK MODE" in proc.stdout and "Yield report" in proc.stdout
    lines = [json.loads(line) for line in results.read_text().splitlines()]
    assert len(lines) == 30
    assert all("survived" in r for r in lines)
    # resumability: second run must skip everything already processed
    proc2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_filter.py"),
         "--mock", "--skip-s2", "--limit", "30", "--results", str(results)],
        capture_output=True, text=True, timeout=120,
    )
    assert "30 already processed" in proc2.stdout
