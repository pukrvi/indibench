"""Tests for scripts/run_benchmark.py — everything runs offline via --mock."""

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "run_benchmark.py"

spec = importlib.util.spec_from_file_location("run_benchmark", SCRIPT)
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)


def test_parse_helpers():
    text = "Explanation: because\nAnswer: 1862\nConfidence: 85%"
    assert rb.extract_answer(text) == "1862"
    assert rb.parse_confidence(text) == 85.0
    assert rb.parse_confidence("no confidence here") is None
    assert rb.extract_answer("bare text") == "bare text"


def test_mock_record_deterministic():
    item = {"id": "ibc-hi-agriculture-abcd1234", "answer": "x"}
    a, b = rb._mock_record(item), rb._mock_record(item)
    assert a == b
    assert a["output_tokens"] > 0 and a["ttft_s"] > 0


def test_aggregate_math():
    records = [
        {"id": "1", "language": "hi", "domain": "d", "correct": True, "confidence": 90.0,
         "ttft_s": 1.0, "tokens_per_sec": 10.0, "output_tokens": 100, "input_tokens": 50,
         "cost_usd": 0.01},
        {"id": "2", "language": "hi", "domain": "d", "correct": False, "confidence": 90.0,
         "ttft_s": 3.0, "tokens_per_sec": 30.0, "output_tokens": 300, "input_tokens": 150,
         "cost_usd": 0.03},
        {"id": "3", "language": "ta", "domain": "d", "error": "boom"},
    ]
    summary = rb.aggregate(records)
    overall = summary["overall"]
    assert overall["items"] == 3 and overall["errors"] == 1
    assert overall["accuracy_pct"] == 50.0
    assert overall["median_ttft_s"] == 2.0
    assert overall["output_tokens"] == 400
    assert overall["cost_usd"] == 0.04
    # 90% stated confidence vs 50% accuracy -> RMS calibration error 40
    assert overall["calibration_error_rms"] == 40.0
    assert summary["by_language"]["hi"]["accuracy_pct"] == 50.0
    assert summary["by_language"]["ta"]["errors"] == 1


def test_mock_run_end_to_end(tmp_path):
    """Full offline run over a slice of the real pool -> complete results folder."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--limit", "25",
         "--out", str(tmp_path), "--run-name", "t1",
         "--input-cost", "1.0", "--output-cost", "3.0"],
        capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    run_dir = tmp_path / "t1"
    for name in ("raw.jsonl", "results.csv", "summary.csv", "summary.json", "overview.html"):
        assert (run_dir / name).exists(), name

    rows = list(csv.DictReader((run_dir / "results.csv").open(encoding="utf-8")))
    assert len(rows) == 25
    for row in rows:
        assert row["correct"] in ("True", "False")
        assert float(row["ttft_s"]) > 0
        assert float(row["tokens_per_sec"]) > 0
        assert int(row["output_tokens"]) > 0
        assert float(row["cost_usd"]) > 0  # pricing was supplied

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["meta"]["mock"] is True
    assert summary["meta"]["unfiltered_pool"] is True
    assert summary["overall"]["items"] == 25
    assert summary["overall"]["cost_usd"] > 0

    html = (run_dir / "overview.html").read_text(encoding="utf-8")
    assert "not official IndiBench scores" in html  # unfiltered-pool caveat
    assert "Median TTFT" in html and "tok/s" in html and "Total cost" in html
    assert "http://" not in html and "https://" not in html  # self-contained

    # resume: rerun with same run-name touches nothing new
    proc2 = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--limit", "25",
         "--out", str(tmp_path), "--run-name", "t1"],
        capture_output=True, text=True, timeout=180)
    assert "25 cached · running 0" in proc2.stdout


def test_run_refuses_non_canary_data(tmp_path):
    bogus = tmp_path / "x.json"
    bogus.write_text('{"examples": []}', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--data", str(bogus),
         "--out", str(tmp_path), "--run-name", "t2"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "canary" in (proc.stdout + proc.stderr)
