from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import jsonlines

from common import validate_example


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate chat-format JSONL datasets.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL file or directory containing JSONL files")
    parser.add_argument("--fail-on-error", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-error-lines", type=int, default=20)
    return parser.parse_args()


def resolve_input_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted([p for p in path.rglob("*.jsonl") if p.is_file()])
    raise FileNotFoundError(f"Input path not found: {path}")


def validate_file(path: Path, max_error_lines: int) -> Tuple[int, int, List[Tuple[int, List[str]]]]:
    valid = 0
    invalid = 0
    error_lines: List[Tuple[int, List[str]]] = []

    with jsonlines.open(path, mode="r") as reader:
        for i, row in enumerate(reader, start=1):
            if not isinstance(row, dict):
                invalid += 1
                if len(error_lines) < max_error_lines:
                    error_lines.append((i, ["row_not_dict"]))
                continue

            errors = validate_example(row)
            if errors:
                invalid += 1
                if len(error_lines) < max_error_lines:
                    error_lines.append((i, errors))
            else:
                valid += 1

    return valid, invalid, error_lines


def main() -> None:
    args = parse_args()
    files = resolve_input_files(args.input)
    if not files:
        raise FileNotFoundError(f"No JSONL files found under: {args.input}")

    total_valid = 0
    total_invalid = 0

    for file in files:
        valid, invalid, error_lines = validate_file(file, args.max_error_lines)
        total_valid += valid
        total_invalid += invalid

        print(f"\nFile: {file}")
        print(f"  valid rows: {valid}")
        print(f"  invalid rows: {invalid}")
        if error_lines:
            print("  sample invalid line numbers:")
            for line_no, errors in error_lines:
                print(f"    line {line_no}: {', '.join(errors)}")

    print("\nSummary")
    print(f"  total valid rows: {total_valid}")
    print(f"  total invalid rows: {total_invalid}")

    if args.fail_on_error and total_invalid > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
