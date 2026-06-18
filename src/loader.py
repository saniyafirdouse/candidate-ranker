"""
loader.py
---------
Streams candidates from candidates.jsonl one at a time.
Never loads the full 465MB file into memory.
"""

import json
import gzip
from pathlib import Path
from typing import Generator


def stream_candidates(filepath: str) -> Generator[dict, None, None]:
    """
    Yields one candidate dict at a time from a .jsonl or .jsonl.gz file.

    Args:
        filepath: path to candidates.jsonl or candidates.jsonl.gz

    Yields:
        dict: one candidate record per line
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Candidate file not found: {filepath}")

    opener = gzip.open if path.suffix == ".gz" else open

    with opener(path, "rt", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  [loader] Skipping line {line_num} — JSON error: {e}")
                continue


def load_all_candidates(filepath: str) -> list[dict]:
    """
    Loads ALL candidates into a list.
    Only use this if you have enough RAM (needs ~2GB for 100K candidates).
    For most machines this is fine. Streaming is used internally.

    Args:
        filepath: path to candidates.jsonl or candidates.jsonl.gz

    Returns:
        list of candidate dicts
    """
    candidates = []
    for candidate in stream_candidates(filepath):
        candidates.append(candidate)
    return candidates


def load_sample(filepath: str, n: int = 50) -> list[dict]:
    """
    Loads only the first N candidates. Useful for testing.

    Args:
        filepath: path to candidates.jsonl
        n:        how many to load

    Returns:
        list of up to n candidate dicts
    """
    candidates = []
    for candidate in stream_candidates(filepath):
        candidates.append(candidate)
        if len(candidates) >= n:
            break
    return candidates


def get_candidate_count(filepath: str) -> int:
    """
    Counts total candidates by streaming. No RAM spike.
    """
    count = 0
    for _ in stream_candidates(filepath):
        count += 1
    return count