"""Standalone judge + metrics (HLE-style; design §4, D-035).

Grades cached predictions against the answer key with an LLM judge
(structured output), then reports accuracy with a 95% Wald CI and RMS
calibration error (HLE's method). Official releases run this twice — one
Anthropic judge, one Google judge — and reconcile disagreements with a
third judge; local users may run a single judge.

    python judge.py --data indibench_text_hi_v2026.XX.json \
        --predictions predictions_<model>.json --judge <judge-model-id>
"""

import argparse
import asyncio
import json
import math
import os
import tempfile
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel


def atomic_write_json(path: Path, payload: dict) -> None:
    """Write via temp file + rename so an interrupted run never corrupts the cache."""
    fd, tmp = tempfile.mkstemp(dir=path.parent or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

JUDGE_PROMPT = """Judge whether the [response]'s final answer is equivalent to the
[correct_answer], allowing small numerical tolerance and treating
transliteration variants of the same Indian-language term as equivalent.
Extract the final answer and the stated confidence (default 100 if absent).

[question]: {question}
[response]: {response}
[correct_answer]: {correct_answer}"""


class Verdict(BaseModel):
    extracted_final_answer: str
    reasoning: str
    correct: bool
    confidence: int


async def judge_one(client: AsyncOpenAI, judge: str, item: dict, prediction: dict,
                    sem: asyncio.Semaphore) -> tuple[str, dict]:
    async with sem:
        completion = await client.chat.completions.parse(
            model=judge,
            messages=[{
                "role": "user",
                "content": JUDGE_PROMPT.format(
                    question=item["question"],
                    response=prediction["response"],
                    correct_answer=item["answer"],
                ),
            }],
            response_format=Verdict,
        )
        verdict = completion.choices[0].message.parsed
        return item["id"], verdict.model_dump()


def calibration_error_rms(confidences: list[float], correctness: list[bool],
                          bin_size: int = 100) -> float:
    """RMS calibration error over confidence-sorted bins (HLE's method)."""
    paired = sorted(zip(confidences, correctness))
    total = 0.0
    n = len(paired)
    for start in range(0, n, bin_size):
        chunk = paired[start:start + bin_size]
        mean_conf = sum(c for c, _ in chunk) / len(chunk)
        mean_acc = 100.0 * sum(1 for _, ok in chunk if ok) / len(chunk)
        total += len(chunk) * (mean_conf - mean_acc) ** 2
    return math.sqrt(total / n) if n else 0.0


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--judge", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    items = {ex["id"]: ex for ex in json.loads(Path(args.data).read_text())["examples"]}
    predictions = json.loads(Path(args.predictions).read_text())
    data_stem = Path(args.data).stem
    out_path = Path(
        f"judged_{data_stem}_{Path(args.predictions).stem}_{args.judge.replace('/', '_')}.json"
    )
    judged: dict = json.loads(out_path.read_text()) if out_path.exists() else {}

    client = AsyncOpenAI()
    sem = asyncio.Semaphore(args.workers)
    todo = [(items[i], p) for i, p in predictions.items() if i in items and i not in judged]
    for coro in asyncio.as_completed([judge_one(client, args.judge, it, p, sem) for it, p in todo]):
        try:
            item_id, verdict = await coro
            judged[item_id] = verdict
            atomic_write_json(out_path, judged)
        except Exception as exc:
            print(f"error: {exc}")

    # Metrics over the FULL dataset (HLE convention): an item with no judged
    # prediction counts as incorrect; calibration uses judged items only.
    total_n = len(items)
    judged_in_data = {i: v for i, v in judged.items() if i in items}
    missing = total_n - len(judged_in_data)
    if missing:
        print(f"warning: {missing}/{total_n} items have no judged prediction "
              f"(counted as incorrect in accuracy)")
    n_correct = sum(1 for v in judged_in_data.values() if v["correct"])
    correct = [v["correct"] for v in judged_in_data.values()]
    confidence = [float(v["confidence"]) for v in judged_in_data.values()]
    accuracy = 100.0 * n_correct / total_n if total_n else 0.0
    ci = 1.96 * math.sqrt(accuracy * (100 - accuracy) / total_n) if total_n else 0.0
    print(f"n={total_n}  accuracy={accuracy:.2f}% ± {ci:.2f}%  "
          f"calibration_error(RMS)={calibration_error_rms(confidence, correct):.1f}")


if __name__ == "__main__":
    asyncio.run(main())
