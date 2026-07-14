"""S5 — Assembly & versioned release (design §3, D-013/D-032).

Injects the canary, carves the private held-out split, stamps the version.
Public: ~2,500 items. Private: ~500 — sized at ~20% of the PUBLIC set
(D-032), i.e. 1/6 of the total pool. Refresh waves every 6 months replace
~1/3 of public items (oldest/easiest first) around a stable anchor subset.
"""

import random
import os
import tempfile
from pathlib import Path

from indibench.canary import make_canary
from indibench.schema import DatasetFile, Item

# D-032: private ≈ 20% of the public set ⇒ 1/6 of the total generated pool.
PRIVATE_FRACTION_OF_TOTAL = 1 / 6


def split_public_private(
    items: list[Item], seed: int, private_fraction: float = PRIVATE_FRACTION_OF_TOTAL
) -> tuple[list[Item], list[Item]]:
    """Deterministic public/private split, stratified by language track so the
    private split can detect overfitting per language, not just overall.

    Determinism is w.r.t. the item SET, not input order: cells are processed
    in sorted language order, sorted by id, with a per-language RNG derived
    from (seed, language). Caveat: cells smaller than ~1/private_fraction
    items round to zero private items — release tooling must check
    per-language private counts before shipping.
    """
    by_lang: dict[str, list[Item]] = {}
    for item in items:
        by_lang.setdefault(item.language.value, []).append(item)
    public: list[Item] = []
    private: list[Item] = []
    for lang, lang_items in sorted(by_lang.items()):
        shuffled = sorted(lang_items, key=lambda i: i.id)
        random.Random(f"{seed}:{lang}").shuffle(shuffled)
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
        # A release file must never be left half-written if the process dies.
        fd, temporary = tempfile.mkstemp(dir=release_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload.model_dump_json(indent=2))
            os.replace(temporary, path)
        except Exception:
            Path(temporary).unlink(missing_ok=True)
            raise
        written.append(path)
    return written
