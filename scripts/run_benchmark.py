"""Run IndiBench against a model and produce a results folder.

One command, one folder of outputs:

    results/<run-name>/
      raw.jsonl        every per-item record (resumable cache — reruns skip done ids)
      results.csv      per-item data: correctness, TTFT, tokens/sec, tokens, cost
      summary.csv      per-language-track aggregates
      summary.json     run metadata + headline numbers
      overview.html    self-contained visual overview (open in any browser)

Works against any OpenAI-compatible endpoint (OpenAI itself, or local
vLLM/Ollama via --base-url). Timing metrics come from streaming: TTFT is
time-to-first-content-token; tokens/sec is output tokens over generation time.

Real run:
    python scripts/run_benchmark.py --model gpt-5-mini \
        --judge gpt-5-mini \
        --input-cost 0.25 --output-cost 2.00

Local model:
    python scripts/run_benchmark.py --model llama3 --base-url http://localhost:11434/v1

Offline dry run (no keys; deterministic fake model — validates the whole
pipeline and produces a real results folder):
    python scripts/run_benchmark.py --mock

Costs: pass --input-cost/--output-cost in USD per **million** tokens (find
them on your provider's pricing page). Default 0 → cost columns report 0.

NOTE: until a filtered release exists, this runs the v0-seed candidate pool
(unfiltered, D-041). Scores are diagnostic only — NOT official IndiBench scores.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = ROOT / "data" / "candidates" / "v0-seed"

SYSTEM_PROMPT = """Your response must be in the following exact format:
Explanation: {your explanation for your answer}
Answer: {your succinct final answer}
Confidence: {your confidence score between 0% and 100% for your answer}

Answer in the same language as the question."""

JUDGE_SYSTEM = (
    "You judge whether a response's final answer is equivalent to a reference "
    "answer. Allow small numerical tolerance and treat transliteration variants "
    "of the same Indian-language term as equivalent. Reply with exactly one "
    "word: CORRECT or INCORRECT."
)
JUDGE_USER = "[question]\n{question}\n\n[response]\n{response}\n\n[reference_answer]\n{reference}"


# ---------------------------------------------------------------- data loading

def load_items(data: Path) -> tuple[list[dict], bool]:
    """Load items from a file or directory of canary-wrapped JSON files.
    Returns (items, is_unfiltered_pool)."""
    files = sorted(data.glob("*.json")) if data.is_dir() else [data]
    if not files:
        raise SystemExit(f"no .json data files found under {data}")
    items, unfiltered = [], False
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "canary" not in payload:
            raise SystemExit(f"{path}: missing canary — refusing to run (not an IndiBench file?)")
        if payload.get("status") == "candidates-unfiltered":
            unfiltered = True
        items.extend(payload["examples"])
    return items, unfiltered


def render_question(item: dict) -> str:
    question = item["question"]
    if item.get("answer_type") == "multipleChoice" and item.get("choices"):
        letters = "ABCDEFGH"
        question += "\n\n" + "\n".join(
            f"{letters[i]}. {c}" for i, c in enumerate(item["choices"]))
    return question


def parse_confidence(text: str) -> float | None:
    match = re.search(r"[Cc]onfidence[:\s]*([0-9]{1,3}(?:\.[0-9]+)?)", text)
    if not match:
        return None
    value = float(match.group(1))
    if 0 < value <= 1.0:  # models answering on a 0-1 scale
        value *= 100.0
    return min(100.0, value)


def extract_answer(text: str) -> str:
    # take everything after the LAST "Answer:" (an explanation that mentions
    # "answer:" must not swallow the real one), cut before the Confidence line
    parts = re.split(r"[Aa]nswer\s*:", text)
    if len(parts) == 1:
        return text.strip()
    return re.split(r"\n[Cc]onfidence", parts[-1])[0].strip()


# ---------------------------------------------------------------- model calls

async def stream_completion(client, model: str, question: str) -> dict:
    """Stream one completion, timing TTFT and generation. Returns raw fields."""
    t0 = time.perf_counter()
    ttft = None
    chunks: list[str] = []
    usage = None
    stream = await client.chat.completions.create(
        model=model,
        stream=True,
        stream_options={"include_usage": True},
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": question}],
    )
    async for chunk in stream:
        if chunk.usage:
            usage = chunk.usage
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            if ttft is None:
                ttft = time.perf_counter() - t0
            chunks.append(chunk.choices[0].delta.content)
    total = time.perf_counter() - t0
    text = "".join(chunks)
    if not text.strip():
        raise RuntimeError("model returned an empty response")
    out_tokens = usage.completion_tokens if usage else None
    in_tokens = usage.prompt_tokens if usage else None
    estimated = out_tokens is None
    if estimated:  # crude fallback when the endpoint reports no usage
        out_tokens = max(1, len(text) // 4)
        in_tokens = max(1, (len(SYSTEM_PROMPT) + len(question)) // 4)
    return {"text": text, "ttft_s": ttft or total, "total_time_s": total,
            "input_tokens": in_tokens, "output_tokens": out_tokens,
            "tokens_estimated": estimated}


async def judge_completion(client, judge_model: str, question: str,
                           response: str, reference: str) -> bool:
    result = await client.chat.completions.create(
        model=judge_model,
        messages=[{"role": "system", "content": JUDGE_SYSTEM},
                  {"role": "user", "content": JUDGE_USER.format(
                      question=question, response=response, reference=reference)}],
    )
    verdict = (result.choices[0].message.content or "").upper()
    if not verdict.strip():
        raise RuntimeError(f"judge {judge_model} returned an empty response")
    return "CORRECT" in verdict and "INCORRECT" not in verdict


# ---------------------------------------------------------------- mock mode

def _mock_record(item: dict) -> dict:
    """Deterministic fake result: hash-derived latencies; ~1/3 items 'correct'."""
    h = hashlib.sha256(item["id"].encode()).digest()
    correct = h[0] % 3 == 0
    answer = item["answer"] if correct else "mock-wrong-answer"
    out_tokens = 40 + h[1] % 160
    ttft = 0.2 + (h[2] / 255) * 1.8
    gen = 0.5 + (h[3] / 255) * 4.0
    return {"text": f"Explanation: mock\nAnswer: {answer}\nConfidence: {50 + h[4] % 50}%",
            "ttft_s": round(ttft, 3), "total_time_s": round(ttft + gen, 3),
            "input_tokens": 120 + h[5] % 80, "output_tokens": out_tokens,
            "tokens_estimated": False, "_mock_correct": correct}


# ---------------------------------------------------------------- per item

async def run_item(item: dict, args, client, judge_client, sem) -> dict:
    record = {"id": item["id"], "language": item["language"], "domain": item["domain"],
              "tags": "|".join(item.get("tags", [])), "answer_type": item["answer_type"]}
    question = render_question(item)
    try:
        if args.mock:
            raw = _mock_record(item)
        else:
            async with sem:
                raw = await stream_completion(client, args.model, question)
        gen_time = max(raw["total_time_s"] - raw["ttft_s"], 1e-6)
        record.update({
            "ttft_s": round(raw["ttft_s"], 4),
            "generation_time_s": round(gen_time, 4),
            "total_time_s": round(raw["total_time_s"], 4),
            "input_tokens": raw["input_tokens"],
            "output_tokens": raw["output_tokens"],
            "tokens_estimated": raw["tokens_estimated"],
            "tokens_per_sec": round(raw["output_tokens"] / gen_time, 2),
            "cost_usd": round(raw["input_tokens"] * args.input_cost / 1e6
                              + raw["output_tokens"] * args.output_cost / 1e6, 6),
            "confidence": parse_confidence(raw["text"]),
            "model_answer": extract_answer(raw["text"]),
            "response": raw["text"],
        })
        if args.mock:
            record["correct"] = raw["_mock_correct"]
        elif judge_client is not None:
            async with sem:
                record["correct"] = await judge_completion(
                    judge_client, args.judge, question, raw["text"], item["answer"])
        else:
            record["correct"] = None  # perf-only run
    except Exception as exc:
        record["error"] = str(exc)
    return record


# ---------------------------------------------------------------- aggregation

def aggregate(records: list[dict]) -> dict:
    ok = [r for r in records if "error" not in r]
    judged = [r for r in ok if r.get("correct") is not None]
    conf = [(float(r["confidence"]), bool(r["correct"])) for r in judged
            if r.get("confidence") is not None]

    def mean(xs):
        return round(statistics.fmean(xs), 3) if xs else None

    def median(xs):
        return round(statistics.median(xs), 3) if xs else None

    def calibration_rms(pairs, bin_size=100):
        if not pairs:
            return None
        pairs = sorted(pairs)
        total = 0.0
        for start in range(0, len(pairs), bin_size):
            chunk = pairs[start:start + bin_size]
            mc = sum(c for c, _ in chunk) / len(chunk)
            ma = 100.0 * sum(1 for _, good in chunk if good) / len(chunk)
            total += len(chunk) * (mc - ma) ** 2
        return round((total / len(pairs)) ** 0.5, 1)

    def slice_stats(rows):
        sliced_judged = [r for r in rows if r.get("correct") is not None]
        return {
            "items": len(rows),
            "errors": sum(1 for r in rows if "error" in r),
            "accuracy_pct": round(100 * sum(r["correct"] for r in sliced_judged)
                                  / len(sliced_judged), 1) if sliced_judged else None,
            "mean_ttft_s": mean([r["ttft_s"] for r in rows if "ttft_s" in r]),
            "median_ttft_s": median([r["ttft_s"] for r in rows if "ttft_s" in r]),
            "mean_tokens_per_sec": mean([r["tokens_per_sec"] for r in rows
                                         if "tokens_per_sec" in r]),
            "output_tokens": sum(r.get("output_tokens", 0) for r in rows),
            "input_tokens": sum(r.get("input_tokens", 0) for r in rows),
            "cost_usd": round(sum(r.get("cost_usd", 0.0) for r in rows), 4),
        }

    by_language: dict[str, dict] = {}
    for lang in sorted({r["language"] for r in records}):
        by_language[lang] = slice_stats([r for r in records if r["language"] == lang])
    by_domain: dict[str, dict] = {}
    for dom in sorted({r["domain"] for r in records}):
        by_domain[dom] = slice_stats([r for r in records if r["domain"] == dom])

    overall = slice_stats(records)
    overall["calibration_error_rms"] = calibration_rms(conf)
    return {"overall": overall, "by_language": by_language, "by_domain": by_domain}


# ---------------------------------------------------------------- outputs

CSV_FIELDS = ["id", "language", "domain", "tags", "answer_type", "correct",
              "confidence", "ttft_s", "generation_time_s", "total_time_s",
              "input_tokens", "output_tokens", "tokens_estimated",
              "tokens_per_sec", "cost_usd", "model_answer", "error"]


def write_outputs(run_dir: Path, records: list[dict], summary: dict, meta: dict) -> None:
    with (run_dir / "results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in sorted(records, key=lambda r: r["id"]):
            writer.writerow(record)

    with (run_dir / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        # static field list: must not depend on data being non-empty
        fields = ["slice", "items", "errors", "accuracy_pct", "mean_ttft_s",
                  "median_ttft_s", "mean_tokens_per_sec", "output_tokens",
                  "input_tokens", "cost_usd"]
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerow({"slice": "OVERALL", **summary["overall"]})
        for lang, stats in summary["by_language"].items():
            writer.writerow({"slice": f"lang:{lang}", **stats})
        for dom, stats in summary["by_domain"].items():
            writer.writerow({"slice": f"domain:{dom}", **stats})

    (run_dir / "summary.json").write_text(
        json.dumps({"meta": meta, **summary}, indent=1, ensure_ascii=False), encoding="utf-8")
    (run_dir / "overview.html").write_text(build_overview(records, summary, meta), encoding="utf-8")


def _slim(records: list[dict]) -> list[dict]:
    """Per-item fields embedded in the dashboard (answers truncated)."""
    slim = []
    for r in records:
        slim.append({
            "id": r["id"], "lang": r["language"], "dom": r["domain"],
            "tags": r.get("tags", ""), "at": r.get("answer_type", ""),
            "ok": r.get("correct"), "conf": r.get("confidence"),
            "ttft": r.get("ttft_s"), "tot": r.get("total_time_s"),
            "tin": r.get("input_tokens"), "tout": r.get("output_tokens"),
            "tps": r.get("tokens_per_sec"), "cost": r.get("cost_usd"),
            "ans": (r.get("model_answer") or "")[:160],
            "err": r.get("error"),
        })
    return slim


def build_overview(records: list[dict], summary: dict, meta: dict) -> str:
    """Interactive single-file dashboard. All data embedded; no external requests."""
    payload = json.dumps({"meta": meta, "records": _slim(records)},
                         ensure_ascii=False).replace("</", "<\\/")
    return _DASHBOARD.replace("__PAYLOAD__", payload)


# Self-contained dashboard template. Chart hues are the dataviz reference
# palette, validated per theme surface (slate dark / paper light / kesar warm)
# with scripts/validate_palette.js — light-surface WARNs on aqua/yellow are
# covered by the relief rule: every bar carries a direct value label and the
# table view always exists.
_DASHBOARD = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IndiBench run dashboard</title>
<style>
:root{--radius:14px;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
body[data-skin="slate"]{color-scheme:dark;
  --page:#0d0d0d;--surface:#1a1a19;--surface2:#232322;--border:#383835;
  --ink:#ffffff;--ink2:#c3c2b7;--ink3:#8b8a80;
  --s-blue:#3987e5;--s-aqua:#199e70;--s-yellow:#c98500;
  --good:#0ca30c;--bad:#d03b3b;--track:#2a2a28;--accent:#3987e5}
body[data-skin="paper"]{color-scheme:light;
  --page:#f9f9f7;--surface:#fcfcfb;--surface2:#f3f3f0;--border:#e5e4e0;
  --ink:#0b0b0b;--ink2:#52514e;--ink3:#8a8983;
  --s-blue:#2a78d6;--s-aqua:#1baf7a;--s-yellow:#eda100;
  --good:#0ca30c;--bad:#d03b3b;--track:#eeede9;--accent:#2a78d6}
body[data-skin="kesar"]{color-scheme:light;
  --page:#f2e9d8;--surface:#faf3e8;--surface2:#f3e9d6;--border:#e3d5b8;
  --ink:#241f16;--ink2:#5c5343;--ink3:#8f8468;
  --s-blue:#2a78d6;--s-aqua:#1baf7a;--s-yellow:#eda100;
  --good:#0ca30c;--bad:#d03b3b;--track:#ece1c9;--accent:#c2410c}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.5 var(--sans);
  -webkit-font-smoothing:antialiased;transition:background .2s,color .2s}
main{max-width:1180px;margin:0 auto;padding:22px 20px 70px}
a{color:var(--accent)}

header.top{display:flex;flex-wrap:wrap;align-items:center;gap:12px;margin-bottom:6px}
h1{font-size:1.35rem;font-weight:700;letter-spacing:-.01em;margin:0}
.chip{font:600 .72rem/1 var(--sans);letter-spacing:.03em;padding:5px 10px;
  border:1px solid var(--border);border-radius:100px;color:var(--ink2);background:var(--surface)}
.chip.mock{color:var(--bad);border-color:var(--bad)}
.spacer{flex:1}
label.sel{display:inline-flex;align-items:center;gap:7px;font-size:.78rem;color:var(--ink3)}
select,input[type=search]{font:inherit;font-size:.82rem;color:var(--ink);
  background:var(--surface);border:1px solid var(--border);border-radius:9px;padding:6px 9px}
select:focus,input:focus{outline:2px solid var(--accent);outline-offset:1px}
.meta{color:var(--ink3);font-size:.78rem;margin:2px 0 14px;font-family:var(--mono)}

.warnbar{border-left:3px solid var(--s-yellow);background:var(--surface);
  border-radius:0 10px 10px 0;padding:9px 14px;font-size:.85rem;color:var(--ink2);margin:0 0 16px}
.warnbar b{color:var(--ink)}

.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:10px;margin:0 0 14px}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:12px 14px 10px}
.kpi .v{font-size:1.5rem;font-weight:750;letter-spacing:-.02em;line-height:1.1;
  font-variant-numeric:tabular-nums}
.kpi .l{color:var(--ink3);font-size:.68rem;font-weight:650;text-transform:uppercase;
  letter-spacing:.06em;margin-top:4px}
.kpi .s{color:var(--ink3);font-size:.7rem;margin-top:1px}

.filters{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:0 0 16px;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:10px 14px}
.filters .n{color:var(--ink3);font-size:.78rem;margin-left:auto;font-variant-numeric:tabular-nums}
button.reset{font:600 .78rem var(--sans);color:var(--ink2);background:var(--surface2);
  border:1px solid var(--border);border-radius:9px;padding:6px 11px;cursor:pointer}
button.reset:hover{color:var(--ink)}

.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:860px){.grid{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:16px 18px 14px;min-width:0}
.card h2{font-size:.92rem;font-weight:700;margin:0 0 2px}
.card .sub{color:var(--ink3);font-size:.74rem;margin:0 0 12px}
.card.wide{grid-column:1/-1}
.empty{color:var(--ink3);font-size:.82rem;padding:14px 0}

.hrow{display:flex;align-items:center;gap:9px;margin:4px 0;min-height:20px}
.hrow .hl{flex:0 0 92px;text-align:right;color:var(--ink2);font:600 .74rem var(--mono);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hrow .htrack{flex:1;height:13px;background:var(--track);border-radius:4px;position:relative}
.hrow .hfill{position:absolute;left:0;top:0;bottom:0;border-radius:0 4px 4px 0;min-width:2px}
.hrow .hv{flex:0 0 76px;font:650 .78rem var(--sans);font-variant-numeric:tabular-nums;color:var(--ink)}
.hrow:hover .htrack{outline:1.5px solid var(--ink3);outline-offset:1px}

.hist{display:flex;align-items:flex-end;gap:2px;height:120px;margin-top:8px}
.hist .col{flex:1;background:var(--s-aqua);border-radius:4px 4px 0 0;min-height:2px;
  position:relative;cursor:default}
.hist .col:hover{outline:1.5px solid var(--ink2);outline-offset:1px}
.histx{display:flex;justify-content:space-between;color:var(--ink3);
  font:.68rem var(--mono);margin-top:5px}

table{border-collapse:collapse;width:100%;font-size:.8rem}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
th{color:var(--ink3);font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;
  cursor:pointer;user-select:none;position:sticky;top:0;background:var(--surface)}
th:hover{color:var(--ink)}
th .dir{font-size:.62rem}
td.num{font-variant-numeric:tabular-nums}
td .ok{color:var(--good);font-weight:650}
td .ko{color:var(--bad);font-weight:650}
td .na{color:var(--ink3)}
tr:hover td{background:var(--surface2)}
.tblwrap{overflow:auto;max-height:430px;border:1px solid var(--border);border-radius:10px}
.tnote{color:var(--ink3);font-size:.74rem;margin-top:8px}

#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--page);
  font:600 .74rem var(--sans);padding:6px 9px;border-radius:8px;opacity:0;
  transform:translate(-50%,-130%);white-space:nowrap;z-index:40;transition:opacity .08s}
footer{color:var(--ink3);font-size:.74rem;margin-top:26px;line-height:1.6}
</style></head>
<body data-skin="slate"><main>

<header class="top">
  <h1>IndiBench run dashboard</h1>
  <span class="chip" id="c-model"></span>
  <span class="chip" id="c-judge"></span>
  <span class="chip mock" id="c-mock" hidden>MOCK RUN</span>
  <span class="spacer"></span>
  <label class="sel">View
    <select id="skin" title="Choose your preferred look">
      <option value="slate">Slate · dark</option>
      <option value="paper">Paper · light</option>
      <option value="kesar">Kesar · warm</option>
    </select>
  </label>
</header>
<div class="meta" id="meta"></div>
<div class="warnbar" id="caveat" hidden>⚠ This run used the <b>unfiltered v0-seed candidate
pool</b> (D-041). Scores are diagnostic only — <b>not official IndiBench scores</b>.
The official benchmark ships after S2–S4 filtering.</div>

<section class="kpis" id="kpis"></section>

<section class="filters">
  <label class="sel">Language <select id="f-lang"></select></label>
  <label class="sel">Domain <select id="f-dom"></select></label>
  <label class="sel">Result <select id="f-res">
    <option value="all">all</option><option value="correct">correct</option>
    <option value="wrong">incorrect</option><option value="error">errors</option>
  </select></label>
  <button class="reset" id="f-reset">Reset</button>
  <span class="n" id="f-count"></span>
</section>

<div class="grid">
  <div class="card"><h2>Accuracy by language</h2><p class="sub">% of judged items correct · filtered</p><div id="ch-acc-lang"></div></div>
  <div class="card"><h2>Accuracy by domain</h2><p class="sub">% of judged items correct · filtered</p><div id="ch-acc-dom"></div></div>
  <div class="card"><h2>Time to first token</h2><p class="sub" id="ttft-sub">distribution across items (s)</p><div class="hist" id="ch-hist"></div><div class="histx" id="ch-histx"></div></div>
  <div class="card"><h2>Median TTFT by language</h2><p class="sub">seconds · lower is better</p><div id="ch-ttft-lang"></div></div>
  <div class="card"><h2>Generation speed by language</h2><p class="sub">mean output tokens per second (tok/s)</p><div id="ch-tps-lang"></div></div>
  <div class="card"><h2>Cost by language</h2><p class="sub" id="cost-sub">USD, from supplied per-1M-token prices</p><div id="ch-cost-lang"></div></div>
  <div class="card wide"><h2>Per-item results</h2><p class="sub">click a column to sort · search filters this table</p>
    <div class="filters" style="margin-bottom:10px"><input type="search" id="f-q" placeholder="search id / answer…" style="flex:1;min-width:160px"><span class="n" id="t-count"></span></div>
    <div class="tblwrap"><table id="tbl"><thead></thead><tbody></tbody></table></div>
    <p class="tnote" id="t-note"></p></div>
</div>

<footer>TTFT = time from request to first streamed content token · tok/s = output
tokens ÷ generation time after first token · cost = tokens × your per-1M prices ·
Total cost here sums the filtered rows. Full data: results.csv (per item),
summary.csv / summary.json (aggregates), raw.jsonl (complete responses).</footer>
</main>
<div id="tip" role="presentation"></div>

<script>
const DATA = __PAYLOAD__;
const R = DATA.records, META = DATA.meta;
const $ = id => document.getElementById(id);

/* ---------- theme dropdown (3 options, persisted) ---------- */
const skinSel = $("skin");
let skin;
try { skin = localStorage.getItem("ib-skin"); } catch(e) {}
if (!skin) skin = matchMedia("(prefers-color-scheme: dark)").matches ? "slate" : "paper";
function applySkin(s){
  document.body.dataset.skin = s;
  // mirror onto <html>: a color-scheme mismatch between html and body stops
  // the body background from propagating to the canvas (dark surround bug)
  document.documentElement.style.colorScheme = (s === "slate") ? "dark" : "light";
}
applySkin(skin); skinSel.value = skin;
skinSel.addEventListener("change", () => {
  applySkin(skinSel.value);
  try { localStorage.setItem("ib-skin", skinSel.value); } catch(e) {}
});

/* ---------- header ---------- */
$("c-model").textContent = "model · " + META.model;
$("c-judge").textContent = META.mock ? "judge · mock self-grading"
  : "judge · " + (META.judge || "none (perf-only)");
if (META.mock) $("c-mock").hidden = false;
if (META.unfiltered_pool) $("caveat").hidden = false;
$("meta").textContent = META.data + " · " + META.timestamp + " UTC · " + R.length + " items";
if (!META.priced) $("cost-sub").textContent = "no pricing supplied — pass --input-cost/--output-cost";

/* ---------- helpers ---------- */
const fmt = {
  pct: v => v == null ? "—" : v.toFixed(1) + "%",
  s:   v => v == null ? "—" : v.toFixed(2) + "s",
  tps: v => v == null ? "—" : v.toFixed(1),
  int: v => v == null ? "—" : v.toLocaleString("en-IN"),
  usd: v => v == null ? "—" : "$" + v.toFixed(4),
};
const mean = a => a.length ? a.reduce((x,y)=>x+y,0)/a.length : null;
const median = a => { if (!a.length) return null;
  const s=[...a].sort((x,y)=>x-y), m=s.length>>1;
  return s.length%2 ? s[m] : (s[m-1]+s[m])/2; };
function calibration(rows){
  const p = rows.filter(r=>r.ok!=null && r.conf!=null)
                .map(r=>[r.conf, r.ok]).sort((a,b)=>a[0]-b[0]);
  if (!p.length) return null;
  let tot=0;
  for (let i=0;i<p.length;i+=100){
    const c=p.slice(i,i+100);
    const mc=mean(c.map(x=>x[0])), ma=100*c.filter(x=>x[1]).length/c.length;
    tot+=c.length*(mc-ma)**2;
  }
  return Math.sqrt(tot/p.length);
}

/* ---------- tooltip ---------- */
const tip = $("tip");
function bindTip(el, text){
  el.addEventListener("mousemove", e => { tip.textContent = text;
    tip.style.left = e.clientX+"px"; tip.style.top = e.clientY-6+"px"; tip.style.opacity = 1; });
  el.addEventListener("mouseleave", () => tip.style.opacity = 0);
}

/* ---------- filters ---------- */
function fillSelect(sel, values){
  sel.innerHTML = "<option value=''>all</option>" +
    values.map(v=>`<option>${v}</option>`).join("");
}
fillSelect($("f-lang"), [...new Set(R.map(r=>r.lang))].sort());
fillSelect($("f-dom"),  [...new Set(R.map(r=>r.dom))].sort());
["f-lang","f-dom","f-res"].forEach(id => $(id).addEventListener("change", render));
$("f-q").addEventListener("input", () => renderTable(current()));
$("f-reset").addEventListener("click", () => { $("f-lang").value=""; $("f-dom").value="";
  $("f-res").value="all"; $("f-q").value=""; render(); });

function current(){
  const L=$("f-lang").value, D=$("f-dom").value, S=$("f-res").value;
  return R.filter(r =>
    (!L || r.lang===L) && (!D || r.dom===D) &&
    (S==="all" || (S==="correct" && r.ok===true) || (S==="wrong" && r.ok===false)
      || (S==="error" && r.err)));
}

/* ---------- KPIs ---------- */
function kpi(v,l,s){ return `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div>${s?`<div class="s">${s}</div>`:""}</div>`; }
function renderKpis(rows){
  const good = rows.filter(r=>!r.err);
  const judged = rows.filter(r=>r.ok!=null);
  const acc = judged.length ? 100*judged.filter(r=>r.ok).length/judged.length : null;
  const cal = calibration(rows);
  const tout = good.reduce((a,r)=>a+(r.tout||0),0), tin = good.reduce((a,r)=>a+(r.tin||0),0);
  const cost = good.reduce((a,r)=>a+(r.cost||0),0);
  let h = kpi(rows.length, "items", "");
  h += kpi(acc==null ? "—" : fmt.pct(acc), "accuracy",
           judged.length ? judged.length+" judged" : "perf-only run");
  h += kpi(fmt.s(median(good.map(r=>r.ttft).filter(v=>v!=null))), "median ttft", "time to first token");
  h += kpi(fmt.tps(mean(good.map(r=>r.tps).filter(v=>v!=null))), "mean tok/s", "generation phase");
  h += kpi(fmt.int(tout), "tokens out", "in: "+fmt.int(tin));
  h += kpi("$"+cost.toFixed(4), "total cost", META.priced ? "" : "no pricing supplied");
  if (cal!=null) h += kpi(cal.toFixed(1), "calibration err", "RMS · lower is better");
  const errs = rows.filter(r=>r.err).length;
  if (errs) h += kpi(errs, "errors", "see results.csv");
  $("kpis").innerHTML = h;
}

/* ---------- horizontal bars (direct labels = relief rule) ---------- */
function groupBy(rows, key){ const m=new Map();
  rows.forEach(r=>{ const k=r[key]; if(!m.has(k)) m.set(k,[]); m.get(k).push(r); });
  return [...m.entries()].sort((a,b)=>a[0]<b[0]?-1:1); }
function hbars(el, entries, cssvar, format, tipfmt){
  el.innerHTML = "";
  const vals = entries.filter(e=>e[1]!=null);
  if (!vals.length){ el.innerHTML = "<p class='empty'>no data for this filter</p>"; return; }
  const peak = Math.max(...vals.map(e=>e[1])) || 1;
  for (const [label, value, n] of entries){
    const row = document.createElement("div"); row.className = "hrow";
    const width = value==null ? 0 : Math.max(2, 100*value/peak);
    row.innerHTML = `<span class="hl">${label}</span>
      <span class="htrack"><span class="hfill" style="width:${width}%;background:var(${cssvar})"></span></span>
      <span class="hv">${value==null ? "—" : format(value)}</span>`;
    bindTip(row, tipfmt(label, value, n));
    el.appendChild(row);
  }
}
function accEntries(rows, key){
  return groupBy(rows, key).map(([k, g]) => {
    const judged = g.filter(r=>r.ok!=null);
    return [k, judged.length ? 100*judged.filter(r=>r.ok).length/judged.length : null, judged.length];
  });
}
function statEntries(rows, key, fn){
  return groupBy(rows, key).map(([k, g]) => { const good=g.filter(r=>!r.err);
    return [k, fn(good), good.length]; });
}

/* ---------- TTFT histogram ---------- */
function renderHist(rows){
  const el = $("ch-hist"), ax = $("ch-histx");
  el.innerHTML = ""; ax.innerHTML = "";
  const vals = rows.filter(r=>!r.err && r.ttft!=null).map(r=>r.ttft);
  if (!vals.length){ el.innerHTML = "<p class='empty'>no data for this filter</p>"; return; }
  const lo = Math.min(...vals), hi = Math.max(...vals), bins = 14;
  const step = (hi-lo)/bins || 1, counts = new Array(bins).fill(0);
  vals.forEach(v => counts[Math.min(bins-1, Math.floor((v-lo)/step))]++);
  const peak = Math.max(...counts) || 1;
  counts.forEach((c,i) => {
    const col = document.createElement("div"); col.className = "col";
    col.style.height = Math.max(2, 100*c/peak) + "%";
    bindTip(col, `${(lo+i*step).toFixed(2)}–${(lo+(i+1)*step).toFixed(2)}s · ${c} item${c===1?"":"s"}`);
    el.appendChild(col);
  });
  ax.innerHTML = `<span>${lo.toFixed(2)}s</span><span>median ${fmt.s(median(vals))}</span><span>${hi.toFixed(2)}s</span>`;
}

/* ---------- table ---------- */
const COLS = [
  ["id","id",r=>`<td style="font-family:var(--mono);font-size:.72rem">${r.id}</td>`],
  ["lang","lang",r=>`<td>${r.lang}</td>`],
  ["dom","domain",r=>`<td>${r.dom}</td>`],
  ["ok","result",r=>`<td>${r.err?'<span class="ko">⚠ error</span>':r.ok===true?'<span class="ok">✓ correct</span>':r.ok===false?'<span class="ko">✗ wrong</span>':'<span class="na">—</span>'}</td>`],
  ["conf","conf %",r=>`<td class="num">${r.conf==null?"—":r.conf}</td>`],
  ["ttft","ttft s",r=>`<td class="num">${r.ttft==null?"—":r.ttft.toFixed(2)}</td>`],
  ["tps","tok/s",r=>`<td class="num">${r.tps==null?"—":r.tps.toFixed(1)}</td>`],
  ["tout","tok out",r=>`<td class="num">${r.tout==null?"—":r.tout}</td>`],
  ["cost","cost $",r=>`<td class="num">${r.cost==null?"—":r.cost.toFixed(5)}</td>`],
];
let sortKey = "id", sortDir = 1;
const CAP = 200;
function renderTable(rows){
  const q = $("f-q").value.trim().toLowerCase();
  let view = q ? rows.filter(r => r.id.toLowerCase().includes(q) ||
                                  (r.ans||"").toLowerCase().includes(q)) : rows;
  view = [...view].sort((a,b)=>{ const x=a[sortKey], y=b[sortKey];
    if (x==null) return 1; if (y==null) return -1;
    return (x<y?-1:x>y?1:0)*sortDir; });
  const head = $("tbl").tHead;
  head.innerHTML = "<tr>" + COLS.map(([k,label]) =>
    `<th data-k="${k}">${label} <span class="dir">${k===sortKey?(sortDir>0?"▲":"▼"):""}</span></th>`).join("") + "</tr>";
  head.querySelectorAll("th").forEach(th => th.addEventListener("click", () => {
    const k = th.dataset.k;
    if (k===sortKey) sortDir *= -1; else { sortKey = k; sortDir = 1; }
    renderTable(current());
  }));
  const body = $("tbl").tBodies[0] || $("tbl").createTBody();
  body.innerHTML = view.slice(0, CAP).map(r => {
    const cells = COLS.map(c => c[2](r)).join("");
    return `<tr title="${(r.ans||"").replace(/"/g,"&quot;")}">${cells}</tr>`;
  }).join("");
  $("t-count").textContent = view.length + " rows";
  $("t-note").textContent = view.length > CAP
    ? `showing first ${CAP} of ${view.length} rows — refine the search, or open results.csv for everything`
    : "hover a row to preview the model's answer · full text in raw.jsonl";
}

/* ---------- render ---------- */
function render(){
  const rows = current();
  $("f-count").textContent = rows.length + " of " + R.length + " items";
  renderKpis(rows);
  hbars($("ch-acc-lang"), accEntries(rows,"lang"), "--s-blue", fmt.pct,
        (l,v,n)=>v==null?`${l} · not judged`:`${l} · ${fmt.pct(v)} of ${n} judged`);
  hbars($("ch-acc-dom"), accEntries(rows,"dom"), "--s-blue", fmt.pct,
        (l,v,n)=>v==null?`${l} · not judged`:`${l} · ${fmt.pct(v)} of ${n} judged`);
  hbars($("ch-ttft-lang"), statEntries(rows,"lang", g=>median(g.map(r=>r.ttft).filter(v=>v!=null))),
        "--s-aqua", fmt.s, (l,v,n)=>`${l} · median ${fmt.s(v)} · ${n} items`);
  hbars($("ch-tps-lang"), statEntries(rows,"lang", g=>mean(g.map(r=>r.tps).filter(v=>v!=null))),
        "--s-blue", fmt.tps, (l,v,n)=>`${l} · ${fmt.tps(v)} tok/s mean · ${n} items`);
  hbars($("ch-cost-lang"), statEntries(rows,"lang", g=>{const c=g.map(r=>r.cost).filter(v=>v!=null);
        return c.length?c.reduce((a,b)=>a+b,0):null;}),
        "--s-yellow", fmt.usd, (l,v,n)=>`${l} · ${fmt.usd(v)} total · ${n} items`);
  renderHist(rows);
  renderTable(rows);
}
render();
</script>
</body></html>'''


# ---------------------------------------------------------------- main

async def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA,
                        help="data file or directory (default: the v0-seed pool)")
    parser.add_argument("--model", default="mock-model")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--judge", default=None,
                        help="judge model id (omit for a perf-only run)")
    parser.add_argument("--judge-base-url", default=None)
    parser.add_argument("--judge-api-key", default=None)
    parser.add_argument("--input-cost", type=float, default=0.0,
                        help="USD per 1M input tokens")
    parser.add_argument("--output-cost", type=float, default=0.0,
                        help="USD per 1M output tokens")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    parser.add_argument("--run-name", default=None,
                        help="results/<run-name>; reuse to resume an interrupted run")
    parser.add_argument("--mock", action="store_true",
                        help="offline dry run: deterministic fake model, no keys needed")
    args = parser.parse_args()

    items, unfiltered = load_items(args.data)
    if args.limit is not None:
        items = items[: args.limit]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_name = args.run_name or f"{args.model.replace('/', '_')}_{stamp}"
    run_dir = args.out / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    raw_path = run_dir / "raw.jsonl"

    # Config sidecar: results in one run folder must all come from the same
    # model/judge/pricing — a resume with different flags would silently mix data.
    run_config = {"model": args.model, "judge": args.judge, "mock": args.mock,
                  "data": str(args.data), "input_cost": args.input_cost,
                  "output_cost": args.output_cost}
    config_path = run_dir / "run_config.json"
    if config_path.exists():
        previous = json.loads(config_path.read_text(encoding="utf-8"))
        if previous != run_config:
            raise SystemExit(
                f"REFUSING to resume: flags differ from this run folder's config "
                f"({config_path}). Re-run with the same flags, or use a new --run-name.")
    else:
        config_path.write_text(json.dumps(run_config, indent=1), encoding="utf-8")

    done: dict[str, dict] = {}
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                # truncated tail from an interrupted run — skip; the item re-runs
                print("warning: skipping a truncated line in raw.jsonl (interrupted run)")
                continue
            if "error" not in record:  # errored items retry
                done[record["id"]] = record
    todo = [it for it in items if it["id"] not in done]
    print(f"{len(items)} items · {len(done)} cached · running {len(todo)}"
          + (" · MOCK MODE (no API calls)" if args.mock else ""))

    client = judge_client = None
    if not args.mock:
        import os

        from openai import AsyncOpenAI
        api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or (
            "local" if args.base_url else None)
        client = AsyncOpenAI(base_url=args.base_url, api_key=api_key)
        if args.judge:
            judge_key = args.judge_api_key or os.environ.get("OPENAI_API_KEY") or (
                "local" if args.judge_base_url else None)
            judge_client = AsyncOpenAI(base_url=args.judge_base_url, api_key=judge_key)

    sem = asyncio.Semaphore(args.workers)
    with raw_path.open("a", encoding="utf-8") as raw_out:
        pending = [run_item(item, args, client, judge_client, sem) for item in todo]
        completed = 0
        for coro in asyncio.as_completed(pending):
            record = await coro
            done[record["id"]] = record
            raw_out.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_out.flush()
            completed += 1
            if completed % 20 == 0:
                print(f"  {completed}/{len(todo)}")

    records = [done[it["id"]] for it in items if it["id"] in done]
    summary = aggregate(records)
    meta = {"model": args.model, "judge": args.judge, "data": str(args.data),
            "timestamp": stamp, "mock": args.mock, "unfiltered_pool": unfiltered,
            "priced": bool(args.input_cost or args.output_cost),
            "input_cost_per_mtok": args.input_cost, "output_cost_per_mtok": args.output_cost}
    write_outputs(run_dir, records, summary, meta)

    overall = summary["overall"]
    print(f"\nrun folder: {run_dir}")
    print(f"  accuracy: {overall['accuracy_pct']}%" if overall["accuracy_pct"] is not None
          else "  accuracy: n/a (perf-only run — pass --judge to grade)")
    ttft = overall["median_ttft_s"]
    speed = overall["mean_tokens_per_sec"]
    print(f"  median TTFT: {f'{ttft}s' if ttft is not None else 'n/a'} · mean speed: "
          f"{f'{speed} tok/s' if speed is not None else 'n/a'}")
    print(f"  tokens out: {overall['output_tokens']:,} · total cost: "
          f"${overall['cost_usd']:,.4f}")
    print("  open overview.html in a browser for the visual report")
    if unfiltered:
        print("  NOTE: unfiltered v0-seed pool — diagnostic scores, not official IndiBench")


if __name__ == "__main__":
    asyncio.run(main())
