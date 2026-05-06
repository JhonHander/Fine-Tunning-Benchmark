from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple

from common import project_root, read_jsonl, write_jsonl


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Split merged dataset into train/validation/test.")
    parser.add_argument("--input", type=Path, default=root / "data" / "final" / "merged.jsonl")
    parser.add_argument("--train-output", type=Path, default=root / "data" / "final" / "train.jsonl")
    parser.add_argument("--val-output", type=Path, default=root / "data" / "final" / "validation.jsonl")
    parser.add_argument("--test-output", type=Path, default=root / "data" / "final" / "test.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--test-ratio", type=float, default=0.1)
    parser.add_argument("--stratify-by-source", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def split_rows(rows: List[dict], train_ratio: float, val_ratio: float, rng: random.Random) -> Tuple[List[dict], List[dict], List[dict]]:
    shuffled = rows.copy()
    rng.shuffle(shuffled)

    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    n_test = n - n_train - n_val

    train_rows = shuffled[:n_train]
    val_rows = shuffled[n_train : n_train + n_val]
    test_rows = shuffled[n_train + n_val : n_train + n_val + n_test]
    return train_rows, val_rows, test_rows


def stratified_split(
    rows: List[dict], train_ratio: float, val_ratio: float, seed: int
) -> Tuple[List[dict], List[dict], List[dict]]:
    by_source: Dict[str, List[dict]] = {}
    for row in rows:
        source = row.get("metadata", {}).get("source", "unknown")
        by_source.setdefault(source, []).append(row)

    rng = random.Random(seed)
    train_all: List[dict] = []
    val_all: List[dict] = []
    test_all: List[dict] = []

    for source, source_rows in sorted(by_source.items()):
        train_rows, val_rows, test_rows = split_rows(source_rows, train_ratio, val_ratio, rng)
        train_all.extend(train_rows)
        val_all.extend(val_rows)
        test_all.extend(test_rows)

    rng.shuffle(train_all)
    rng.shuffle(val_all)
    rng.shuffle(test_all)
    return train_all, val_all, test_all


def main() -> None:
    args = parse_args()
    total_ratio = args.train_ratio + args.val_ratio + args.test_ratio
    if abs(total_ratio - 1.0) > 1e-9:
        raise ValueError("train/val/test ratios must sum to 1.0")

    rows = read_jsonl(args.input)
    rng = random.Random(args.seed)

    if args.stratify_by_source:
        train_rows, val_rows, test_rows = stratified_split(
            rows,
            train_ratio=args.train_ratio,
            val_ratio=args.val_ratio,
            seed=args.seed,
        )
    else:
        train_rows, val_rows, test_rows = split_rows(rows, args.train_ratio, args.val_ratio, rng)

    write_jsonl(args.train_output, train_rows)
    write_jsonl(args.val_output, val_rows)
    write_jsonl(args.test_output, test_rows)

    print(f"Input rows: {len(rows)}")
    print(f"Train rows: {len(train_rows)}")
    print(f"Validation rows: {len(val_rows)}")
    print(f"Test rows: {len(test_rows)}")
    print(f"Saved train: {args.train_output}")
    print(f"Saved validation: {args.val_output}")
    print(f"Saved test: {args.test_output}")


if __name__ == "__main__":
    main()
