"""Rule packs: YAML parameters + a small deterministic engine.

The AI never does arithmetic. It only reads the paper; everything below is ordinary code.
"""
import os
from functools import lru_cache
from pathlib import Path

import yaml

from . import engine

MODULES = ("payslip", "loan", "bill", "khata")
PACK_DIR = Path(os.getenv("RULE_PACK_DIR", Path(__file__).parent / "packs"))


@lru_cache(maxsize=None)
def load_pack(module: str) -> dict:
    if module not in MODULES:
        raise KeyError(f"unknown module: {module}")
    with open(PACK_DIR / f"{module}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def all_params() -> dict:
    """Parameters for the frontend (so numbers like 208 or 24% live in one place)."""
    return {m: {**load_pack(m)["params"], "source": load_pack(m)["source"], "version": load_pack(m)["version"]} for m in MODULES}


def check(module: str, values: dict, as_of=None) -> dict:
    pack = load_pack(module)
    return getattr(engine, module)(values, pack["params"], as_of=as_of)
