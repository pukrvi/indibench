"""S5 — Assembly & versioned release (design §3, D-013/D-032).

Injects the canary, carves the private held-out split, stamps the version.
Public: ~2,500 items. Private: ~500 (~20%), never published (D-032).
Refresh waves every 6 months replace ~1/3 of public items (oldest/easiest
first) around a stable anchor subset.
"""

import json
import random
from pathlib import Path

from indibench.canary import make_canary
from indibench.schema import DatasetFile, Item

PRIVATE_FRACTION = 0.20  # D-032


def split_public_private(
    items: list[Item], seed: int, private_fraction: float = PRIVATE_FRACTION
) -> tuple[list[Item], list[Item]]:
    """Deterministic public/private split, stratified by language track so the
    private split can detect overfitting per language, not just overall."""
    rng = random.Random(seed)
    by_lang: dict[str, list[Item]] = {}
    for item in items:
        by_lang.setdefault(item.language.value, []).append(item)
    public: list[Item] = []
    private: list[Item] = []
    for lang_items in by_lang.values():
        shuffled = lang_items[:]
        rng.shuffle(shuffled)
        n_private = round(len(shuffled) * private_fraction)
        private.extend(shuffled[:n_private])
        public.extend(shuffled[n_private:])
    return public, private


def write_release(
    items: list[Item], out_dir: Path, version: str, canary_guid: str
) -> list[Path]:
    """Write one canary-wrapped JSON file per language track:
    <out_dir>/<version>/indibench_text_<lang>_<version>.json
    """
    release_dir = out_dir / version
    release_dir.mkdir(parents=True, exist_ok=True)
    canary = make_canary(canary_guid)
    written: list[Path] = []
    by_lang: dict[str, list[Item]] = {}
    for item in items:
        by_lang.setdefault(item.language.value, []).append(item)
    for lang, lang_items in sorted(by_lang.items()):
        payload = DatasetFile(canary=canary, examples=lang_items)
        path = release_dir / f"indibench_text_{lang}_{version}.json"
        path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
        written.append(path)
    return written
