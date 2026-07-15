from __future__ import annotations

import hashlib
import json
from pathlib import Path


CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "cache"


def cache_key(payload: object, prefix: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def read_cache(key: str) -> str | None:
    path = CACHE_DIR / f"{key}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_cache(key: str, value: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.txt").write_text(value, encoding="utf-8")
