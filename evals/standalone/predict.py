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
from pathlib import Path

from openai import AsyncOpenAI

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
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    payload = json.loads(Path(args.data).read_text(encoding="utf-8"))
    out_path = Path(f"predictions_{args.model.replace('/', '_')}.json")
    done: dict = json.loads(out_path.read_text()) if out_path.exists() else {}

    todo = [ex for ex in payload["examples"] if ex["id"] not in done]
    print(f"{len(done)} cached, {len(todo)} to run")

    client = AsyncOpenAI(base_url=args.base_url)
    sem = asyncio.Semaphore(args.workers)
    for coro in asyncio.as_completed([predict_one(client, args.model, ex, sem) for ex in todo]):
        try:
            item_id, result = await coro
            done[item_id] = result
            out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1))
        except Exception as exc:  # keep going; cached items make retries cheap
            print(f"error: {exc}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
