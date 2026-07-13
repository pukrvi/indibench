"""Standalone prediction runner (HLE-style; design §4, D-012/D-015).

Zero-framework local evaluation: point it at a released data file and any
OpenAI-compatible endpoint (including local vLLM/Ollama on Ubuntu). Results
are cached per-item so interrupted runs resume instead of re-spending.

    python predict.py --data indibench_text_hi_v2026.XX.json \
        --model <model-id> --base-url http://localhost:8000/v1
"""

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from openai import AsyncOpenAI


def atomic_write_json(path: Path, payload: dict) -> None:
    """Write via temp file + rename so an interrupted run never corrupts the cache."""
    fd, tmp = tempfile.mkstemp(dir=path.parent or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)

SYSTEM_PROMPT = """Your response must be in the following exact format:
Explanation: {your explanation for your answer}
Answer: {your succinct final answer}
Confidence: {your confidence score between 0% and 100% for your answer}

Answer in the same language as the question."""


async def predict_one(client: AsyncOpenAI, model: str, item: dict, sem: asyncio.Semaphore) -> tuple[str, dict]:
    async with sem:
        question = item["question"]
        if item["answer_type"] == "multipleChoice" and item.get("choices"):
            letters = "ABCDEFGH"
            question += "\n\n" + "\n".join(
                f"{letters[i]}. {c}" for i, c in enumerate(item["choices"])
            )
        response = await client.chat.completions.create(
            model=model,
            temperature=0.0,
            max_completion_tokens=8192,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ],
        )
        return item["id"], {
            "model": model,
            "response": response.choices[0].message.content,
            "usage": response.usage.model_dump() if response.usage else None,
        }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--api-key", default=None,
                        help="defaults to $OPENAI_API_KEY; a dummy value is used "
                             "automatically when --base-url points at a local server")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    payload = json.loads(Path(args.data).read_text(encoding="utf-8"))
    data_stem = Path(args.data).stem
    out_path = Path(f"predictions_{data_stem}_{args.model.replace('/', '_')}.json")
    done: dict = json.loads(out_path.read_text()) if out_path.exists() else {}

    todo = [ex for ex in payload["examples"] if ex["id"] not in done]
    print(f"{len(done)} cached, {len(todo)} to run")

    api_key = args.api_key or os.environ.get("OPENAI_API_KEY") or (
        "local" if args.base_url else None
    )
    client = AsyncOpenAI(base_url=args.base_url, api_key=api_key)
    sem = asyncio.Semaphore(args.workers)
    for coro in asyncio.as_completed([predict_one(client, args.model, ex, sem) for ex in todo]):
        try:
            item_id, result = await coro
            done[item_id] = result
            atomic_write_json(out_path, done)
        except Exception as exc:  # keep going; cached items make retries cheap
            print(f"error: {exc}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
