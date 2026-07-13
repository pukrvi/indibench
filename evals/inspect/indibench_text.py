"""IndiBench-Text as an Inspect AI task (design §4, D-012).

Follows the inspect_evals/hle pattern: a system prompt that elicits
Explanation / Answer / Confidence, model-graded equivalence scoring, and
accuracy + calibration reporting. Runs against any released data file
(the canary wrapper is validated, then stripped, at load time).

Usage (once data exists):
    inspect eval evals/inspect/indibench_text.py -T data_file=data/v2026.XX/indibench_text_hi_v2026.XX.json --model <model>
"""

import json
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.scorer import model_graded_qa
from inspect_ai.solver import generate, system_message

from indibench.canary import is_valid_canary

SYSTEM_PROMPT = """Your response must be in the following exact format:
Explanation: {your explanation for your answer}
Answer: {your succinct final answer}
Confidence: {your confidence score between 0% and 100% for your answer}

Answer in the same language as the question."""

GRADER_TEMPLATE = """Judge whether [answer] is equivalent to [criterion],
allowing small numerical tolerance and treating transliteration variants of
the same Indian-language term as equivalent. Focus only on the final answer,
not the explanation.

[question]: {question}
[answer]: {answer}
[criterion]: {criterion}"""


def _load_samples(data_file: str) -> list[Sample]:
    payload = json.loads(Path(data_file).read_text(encoding="utf-8"))
    if not is_valid_canary(payload.get("canary", "")):
        raise ValueError(f"{data_file}: missing or malformed canary — refusing to run")
    samples = []
    for ex in payload["examples"]:
        question = ex["question"]
        if ex["answer_type"] == "multipleChoice" and ex.get("choices"):
            letters = "ABCDEFGH"
            rendered = "\n".join(f"{letters[i]}. {c}" for i, c in enumerate(ex["choices"]))
            question = f"{question}\n\n{rendered}"
        samples.append(
            Sample(
                id=ex["id"],
                input=question,
                target=ex["answer"],
                metadata={
                    "language": ex["language"],
                    "domain": ex["domain"],
                    "tags": ex.get("tags", []),
                },
            )
        )
    return samples


@task
def indibench_text(data_file: str, grader_model: str | None = None) -> Task:
    """IndiBench-Text. Per D-035, official runs use dual judges (one Anthropic +
    one Google) — pass each via grader_model in separate runs; the release
    tooling reconciles disagreements with a third-judge tiebreak."""
    return Task(
        dataset=MemoryDataset(_load_samples(data_file)),
        solver=[system_message(SYSTEM_PROMPT), generate()],
        scorer=model_graded_qa(template=GRADER_TEMPLATE, model=grader_model),
    )
