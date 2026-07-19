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
    # fractional confidence scales up; >100 caps
    assert rb.parse_confidence("Confidence: 0.95") == 95.0
    assert rb.parse_confidence("Confidence: 250") == 100.0
    # LAST Answer: wins when the explanation mentions "answer:"
    tricky = "The answer: A is wrong here. Answer: B\nConfidence: 60%"
    assert rb.extract_answer(tricky) == "B"


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
    assert "Median TTFT" in html and "tok/s" in html
    assert "http://" not in html and "https://" not in html  # self-contained
    # dashboard: theme dropdown with exactly the three skins, data embedded
    assert '<select id="skin"' in html
    for skin in ("slate", "paper", "kesar"):
        assert f'value="{skin}"' in html
    assert "__PAYLOAD__" not in html and '"records":' in html
    # interactivity hooks: filters + sortable table + tooltip layer
    for hook in ('id="f-lang"', 'id="f-dom"', 'id="f-res"', 'id="f-q"',
                 'id="tbl"', 'id="tip"', 'id="kpis"'):
        assert hook in html, hook

    # resume: rerun with the SAME flags touches nothing new
    same_flags = [sys.executable, str(SCRIPT), "--mock", "--limit", "25",
                  "--out", str(tmp_path), "--run-name", "t1",
                  "--input-cost", "1.0", "--output-cost", "3.0"]
    proc2 = subprocess.run(same_flags, capture_output=True, text=True, timeout=180)
    assert "25 cached · running 0" in proc2.stdout
    # resume with DIFFERENT flags must refuse (would silently mix data)
    proc3 = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--limit", "25",
         "--out", str(tmp_path), "--run-name", "t1"],  # pricing omitted
        capture_output=True, text=True, timeout=180)
    assert proc3.returncode != 0 and "REFUSING to resume" in (proc3.stdout + proc3.stderr)
    # truncated raw.jsonl tail must not kill the resume
    with (run_dir / "raw.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"id": "ibc-trunc')
    proc4 = subprocess.run(same_flags, capture_output=True, text=True, timeout=180)
    assert proc4.returncode == 0, proc4.stderr
    assert "truncated line" in proc4.stdout


def test_hostile_model_answer_cannot_break_the_payload():
    """A '<!--<script' in a model answer must never escape the JSON payload."""
    hostile = {"id": "ibc-hi-agriculture-x", "language": "hi", "domain": "agriculture",
               "answer_type": "exactMatch", "correct": False, "confidence": 50.0,
               "ttft_s": 1.0, "generation_time_s": 1.0, "total_time_s": 2.0,
               "input_tokens": 10, "output_tokens": 10, "tokens_per_sec": 10.0,
               "cost_usd": 0.0, "model_answer": '</script><!--<script>alert(1)',
               "response": "x"}
    summary = rb.aggregate([hostile])
    html = rb.build_overview([hostile], summary,
                             {"model": "m", "judge": None, "data": "d", "timestamp": "t",
                              "mock": True, "unfiltered_pool": True, "priced": False})
    start = html.index("const DATA = ") + len("const DATA = ")
    payload = html[start:html.index(";\n", start)]
    assert "<" not in payload            # every '<' is <-escaped
    assert json.loads(payload)["records"][0]["ans"].startswith("</script>")


def test_effort_recorded_and_pinned(tmp_path):
    """--effort is captured in meta + run_config and shown in the dashboard;
    resuming without it refuses (config mismatch)."""
    flags = [sys.executable, str(SCRIPT), "--mock", "--limit", "5",
             "--out", str(tmp_path), "--run-name", "eff", "--effort", "max"]
    proc = subprocess.run(flags, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, proc.stderr
    assert "[max]" in proc.stdout  # console summary mentions the effort
    run_dir = tmp_path / "eff"

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["meta"]["effort"] == "max"
    config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    assert config["effort"] == "max"
    html = (run_dir / "overview.html").read_text(encoding="utf-8")
    assert '"effort": "max"' in html or '"effort":"max"' in html  # embedded payload
    # header-chip JS renders "model · <name> [<effort>]" when META.effort is set
    assert 'META.effort ? " [" + META.effort + "]"' in html

    # resume WITHOUT --effort must refuse — it would silently mix data
    proc2 = subprocess.run(flags[:-2], capture_output=True, text=True, timeout=180)
    assert proc2.returncode != 0
    assert "REFUSING to resume" in (proc2.stdout + proc2.stderr)

    # default run-name gets the effort suffix: <model>_<effort>_<stamp>
    proc3 = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--limit", "1",
         "--out", str(tmp_path), "--effort", "low"],
        capture_output=True, text=True, timeout=180)
    assert proc3.returncode == 0, proc3.stderr
    assert any(p.name.startswith("mock-model_low_") for p in tmp_path.iterdir())


def test_zero_item_run_does_not_crash(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--limit", "0",
         "--out", str(tmp_path), "--run-name", "empty"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "empty" / "summary.csv").exists()
    assert (tmp_path / "empty" / "overview.html").exists()


def test_run_refuses_non_canary_data(tmp_path):
    bogus = tmp_path / "x.json"
    bogus.write_text('{"examples": []}', encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--mock", "--data", str(bogus),
         "--out", str(tmp_path), "--run-name", "t2"],
        capture_output=True, text=True, timeout=60)
    assert proc.returncode != 0
    assert "canary" in (proc.stdout + proc.stderr)
