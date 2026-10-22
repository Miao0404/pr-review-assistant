"""Shared paths, prices and small helpers for the context ablation experiment."""

import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

PRS_FILE = DATA_DIR / "prs.json"              # fixed PR sample (written once, before any agent run)
GT_FILE = DATA_DIR / "ground_truth.json"      # human issues extracted per PR
RUNS_FILE = DATA_DIR / "runs.jsonl"           # one line per agent run
JUDGE_FILE = DATA_DIR / "judgements.jsonl"    # one line per (run, judge model)

REPOS = ["fastapi/fastapi", "psf/requests", "encode/httpx"]  # flask dropped before any run: almost no line-level reviews
CONDITIONS = ["C0", "C1", "C2"]
SEED = 42

# USD per million tokens (input, output). Check against current price pages before running.
PRICES = {
    "claude-sonnet-5": (2.0, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1": (2.0, 8.0),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES.get(model, (3.0, 15.0))  # unknown model: assume expensive
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def repeat_subset(prs: list[dict], n: int = 10) -> set[str]:
    """PRs that get 3 runs per condition instead of 1. Chosen by fixed seed, not by hand."""
    keys = sorted(p["key"] for p in prs)
    rng = random.Random(SEED)
    return set(rng.sample(keys, min(n, len(keys))))
