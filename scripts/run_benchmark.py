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
from html import escape
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
    match = re.search(r"[Cc]onfidence[:\s]*([0-9]{1,3})", text)
    if match:
        return min(100.0, float(match.group(1)))
    return None


def extract_answer(text: str) -> str:
    match = re.search(r"[Aa]nswer\s*:\s*(.+?)(?:\n[Cc]onfidence|$)", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


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
        fields = ["slice"] + list(next(iter(summary["by_language"].values())).keys())
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerow({"slice": "OVERALL",
                         **{k: v for k, v in summary["overall"].items() if k in fields}})
        for lang, stats in summary["by_language"].items():
            writer.writerow({"slice": f"lang:{lang}", **stats})
        for dom, stats in summary["by_domain"].items():
            writer.writerow({"slice": f"domain:{dom}", **stats})

    (run_dir / "summary.json").write_text(
        json.dumps({"meta": meta, **summary}, indent=1, ensure_ascii=False), encoding="utf-8")
    (run_dir / "overview.html").write_text(build_overview(summary, meta), encoding="utf-8")


def _bar_rows(slices: dict, key: str, fmt: str, color: str) -> str:
    values = {k: v[key] for k, v in slices.items() if v.get(key) is not None}
    if not values:
        return "<p class='na'>no data</p>"
    peak = max(values.values()) or 1
    rows = []
    for name, value in values.items():
        width = max(2, round(100 * value / peak))
        rows.append(
            f"<div class='row'><span class='lbl'>{escape(str(name))}</span>"
            f"<span class='track'><span class='fill' style='width:{width}%;background:{color}'></span></span>"
            f"<span class='val'>{format(value, fmt)}</span></div>")
    return "".join(rows)


def build_overview(summary: dict, meta: dict) -> str:
    overall = summary["overall"]
    judged = overall["accuracy_pct"] is not None
    caveat = ("<div class='warn'>⚠ This run used the <b>unfiltered v0-seed candidate pool</b> "
              "(D-041). Scores are diagnostic only — <b>not official IndiBench scores</b>. "
              "The official benchmark ships after S2–S4 filtering.</div>"
              if meta.get("unfiltered_pool") else "")
    tiles = [
        ("Items", overall["items"], ""),
        ("Accuracy", f"{overall['accuracy_pct']}%" if judged else "perf-only run", ""),
        ("Median TTFT", f"{overall['median_ttft_s']}s", "time to first token"),
        ("Mean speed", f"{overall['mean_tokens_per_sec']} tok/s", "generation phase"),
        ("Tokens out", f"{overall['output_tokens']:,}", f"in: {overall['input_tokens']:,}"),
        ("Total cost", f"${overall['cost_usd']:,.4f}",
         "" if meta.get("priced") else "no pricing supplied — pass --input-cost/--output-cost"),
    ]
    if overall.get("calibration_error_rms") is not None:
        tiles.append(("Calibration error", overall["calibration_error_rms"], "RMS, lower is better"))
    if overall["errors"]:
        tiles.append(("Errors", overall["errors"], "see results.csv"))
    tile_html = "".join(
        f"<div class='tile'><div class='k'>{escape(str(v))}</div>"
        f"<div class='t'>{escape(label)}</div><div class='s'>{escape(sub)}</div></div>"
        for label, v, sub in tiles)

    sections = []
    if judged:
        sections.append(("Accuracy by language track (%)",
                         _bar_rows(summary["by_language"], "accuracy_pct", ".1f", "#0f766e")))
        sections.append(("Accuracy by domain (%)",
                         _bar_rows(summary["by_domain"], "accuracy_pct", ".1f", "#0f766e")))
    sections.append(("Median TTFT by language (s)",
                     _bar_rows(summary["by_language"], "median_ttft_s", ".2f", "#c2410c")))
    sections.append(("Mean tokens/sec by language",
                     _bar_rows(summary["by_language"], "mean_tokens_per_sec", ".1f", "#7c3aed")))
    sections.append(("Output tokens by language",
                     _bar_rows(summary["by_language"], "output_tokens", ",d", "#b45309")))
    sections.append(("Cost by language (USD)",
                     _bar_rows(summary["by_language"], "cost_usd", ".4f", "#15803d")))
    section_html = "".join(
        f"<section><h2>{escape(title)}</h2>{body}</section>" for title, body in sections)

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IndiBench run — {escape(meta['model'])}</title>
<style>
body{{margin:0;background:#faf8f5;color:#1c1a17;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}}
@media(prefers-color-scheme:dark){{body{{background:#15130f;color:#f0ebe3}}
 .tile,section{{background:#1e1b16!important;border-color:#332c22!important}}
 .track{{background:#332c22!important}} .warn{{background:#2a2113!important}}}}
main{{max-width:900px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:1.5rem;margin:.2em 0}} h2{{font-size:1.02rem;margin:0 0 12px}}
.meta{{color:#8a8073;font-size:.85rem;margin-bottom:18px}}
.warn{{border-left:3px solid #b45309;background:#fdf3e3;padding:10px 14px;border-radius:0 8px 8px 0;margin:14px 0;font-size:.9rem}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin:18px 0}}
.tile,section{{border:1px solid #e7ded2;border-radius:12px;background:#fff;padding:14px 16px}}
.tile .k{{font-size:1.4rem;font-weight:700}} .tile .t{{color:#6b6156;font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}}
.tile .s{{color:#938a7e;font-size:.72rem;margin-top:2px}}
section{{margin:14px 0}}
.row{{display:flex;align-items:center;gap:10px;margin:5px 0;font-size:.85rem}}
.lbl{{flex:0 0 130px;text-align:right;color:#6b6156;font-family:ui-monospace,Menlo,monospace;font-size:.78rem}}
.track{{flex:1;height:14px;background:#f3efe9;border-radius:7px;overflow:hidden}}
.fill{{display:block;height:100%;border-radius:7px}}
.val{{flex:0 0 84px;font-variant-numeric:tabular-nums;font-weight:600}}
.na{{color:#938a7e}}
footer{{color:#938a7e;font-size:.78rem;margin-top:26px}}
</style></head><body><main>
<h1>IndiBench run overview</h1>
<div class="meta">model <b>{escape(meta['model'])}</b>
 · data {escape(meta['data'])} · {escape(meta['timestamp'])}
 · judge {escape('mock self-grading' if meta.get('mock') else str(meta.get('judge') or 'none (perf-only)'))}{' · MOCK RUN' if meta.get('mock') else ''}</div>
{caveat}
<div class="tiles">{tile_html}</div>
{section_html}
<footer>Generated by scripts/run_benchmark.py · per-item data in results.csv ·
aggregates in summary.csv / summary.json · TTFT = time to first streamed token;
tokens/sec = output tokens ÷ generation time (after first token).</footer>
</main></body></html>"""


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

    done: dict[str, dict] = {}
    if raw_path.exists():
        for line in raw_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
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
    print(f"  median TTFT: {overall['median_ttft_s']}s · mean speed: "
          f"{overall['mean_tokens_per_sec']} tok/s")
    print(f"  tokens out: {overall['output_tokens']:,} · total cost: "
          f"${overall['cost_usd']:,.4f}")
    print("  open overview.html in a browser for the visual report")
    if unfiltered:
        print("  NOTE: unfiltered v0-seed pool — diagnostic scores, not official IndiBench")


if __name__ == "__main__":
    asyncio.run(main())
