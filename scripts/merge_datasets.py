from __future__ import annotations

import argparse
import math
import random
from fractions import Fraction
from pathlib import Path
from typing import Dict, List

from common import normalize_weight_map, project_root, read_jsonl, write_jsonl


SOURCES = ("medquad", "bioasq", "pubmedqa")


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Merge processed datasets with configurable source weights.")
    parser.add_argument("--medquad-input", type=Path, default=root / "data" / "processed" / "medquad_chat.jsonl")
    parser.add_argument("--bioasq-input", type=Path, default=root / "data" / "processed" / "bioasq_chat.jsonl")
    parser.add_argument("--pubmedqa-input", type=Path, default=root / "data" / "processed" / "pubmedqa_chat.jsonl")
    parser.add_argument("--output", type=Path, default=root / "data" / "final" / "merged.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--medquad-weight", type=float, default=0.5)
    parser.add_argument("--bioasq-weight", type=float, default=0.3)
    parser.add_argument("--pubmedqa-weight", type=float, default=0.2)
    parser.add_argument("--mode", type=str, default="downsample_strict", choices=["downsample_strict"])
    return parser.parse_args()


def _lcm(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b)


def weights_to_integer_ratios(weights: Dict[str, float]) -> Dict[str, int]:
    fractions = {k: Fraction(v).limit_denominator(1000) for k, v in weights.items()}
    common_denominator = 1
    for frac in fractions.values():
        common_denominator = _lcm(common_denominator, frac.denominator)

    integers = {
        key: int(frac.numerator * (common_denominator // frac.denominator))
        for key, frac in fractions.items()
    }

    gcd_all = 0
    for value in integers.values():
        gcd_all = value if gcd_all == 0 else math.gcd(gcd_all, value)

    return {k: v // gcd_all for k, v in integers.items()}


def sample_strict_ratio(
    data_by_source: Dict[str, List[dict]],
    weights: Dict[str, float],
    seed: int,
) -> List[dict]:
    normalized_weights = normalize_weight_map(weights)
    ratios = weights_to_integer_ratios(normalized_weights)

    counts = {src: len(rows) for src, rows in data_by_source.items()}
    k_max = min(counts[src] // ratios[src] for src in SOURCES)
    if k_max <= 0:
        raise ValueError(
            "Not enough data to satisfy strict weighted downsampling without duplication. "
            f"Counts={counts}, ratios={ratios}"
        )

    rng = random.Random(seed)
    sampled: List[dict] = []
    for src in SOURCES:
        target_n = k_max * ratios[src]
        sampled.extend(rng.sample(data_by_source[src], target_n))

    rng.shuffle(sampled)
    return sampled


def main() -> None:
    args = parse_args()
    data_by_source = {
        "medquad": read_jsonl(args.medquad_input),
        "bioasq": read_jsonl(args.bioasq_input),
        "pubmedqa": read_jsonl(args.pubmedqa_input),
    }

    weights = {
        "medquad": args.medquad_weight,
        "bioasq": args.bioasq_weight,
        "pubmedqa": args.pubmedqa_weight,
    }

    merged = sample_strict_ratio(data_by_source, weights=weights, seed=args.seed)
    write_jsonl(args.output, merged)

    total = len(merged)
    print(f"Merged total examples: {total}")
    for src in SOURCES:
        c = sum(1 for row in merged if row.get("metadata", {}).get("source") == src)
        print(f"  {src}: {c} ({(c / total) * 100:.2f}%)")
    print(f"Saved to: {args.output}")


if __name__ == "__main__":
    main()
