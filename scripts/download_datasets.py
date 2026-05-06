from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from datasets import load_dataset

from common import project_root


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(
        description="Download medical datasets from Hugging Face and save them under data/raw/."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=root / "data" / "raw",
        help="Root raw-data directory where dataset JSONL files will be written.",
    )
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument("--medquad-dataset", type=str, default="lavita/MedQuAD")
    parser.add_argument("--medquad-split", type=str, default="train")

    parser.add_argument("--bioasq-dataset", type=str, default="bigbio/bioasq")
    parser.add_argument("--bioasq-config", type=str, default=None)
    parser.add_argument("--bioasq-split", type=str, default="train")

    parser.add_argument("--pubmedqa-dataset", type=str, default="qiaojin/PubMedQA")
    parser.add_argument("--pubmedqa-config", type=str, default="pqa_labeled")
    parser.add_argument("--pubmedqa-split", type=str, default="train")

    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["medquad", "bioasq", "pubmedqa"],
        choices=["medquad", "bioasq", "pubmedqa"],
        help="One or more dataset names to download.",
    )
    parser.add_argument(
        "--force-overwrite",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Overwrite output JSONL files if they already exist.",
    )
    return parser.parse_args()


def export_split_to_jsonl(
    dataset_name: str,
    config: Optional[str],
    split: str,
    output_file: Path,
    seed: int,
    force_overwrite: bool,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.exists() and not force_overwrite:
        print(f"[skip] {output_file} already exists (use --force-overwrite to replace).")
        return

    print(f"[download] {dataset_name} config={config} split={split}")
    if config:
        ds = load_dataset(dataset_name, config, split=split)
    else:
        ds = load_dataset(dataset_name, split=split)

    ds = ds.shuffle(seed=seed)
    ds.to_json(str(output_file), lines=True, force_ascii=False)
    print(f"[saved] {output_file} rows={len(ds)}")


def main() -> None:
    args = parse_args()

    selected = set(args.datasets)
    root = args.output_root

    if "medquad" in selected:
        export_split_to_jsonl(
            dataset_name=args.medquad_dataset,
            config=None,
            split=args.medquad_split,
            output_file=root / "medquad" / "medquad_train.jsonl",
            seed=args.seed,
            force_overwrite=args.force_overwrite,
        )

    if "bioasq" in selected:
        export_split_to_jsonl(
            dataset_name=args.bioasq_dataset,
            config=args.bioasq_config,
            split=args.bioasq_split,
            output_file=root / "bioasq" / "bioasq_train.jsonl",
            seed=args.seed,
            force_overwrite=args.force_overwrite,
        )

    if "pubmedqa" in selected:
        export_split_to_jsonl(
            dataset_name=args.pubmedqa_dataset,
            config=args.pubmedqa_config,
            split=args.pubmedqa_split,
            output_file=root / "pubmedqa" / "pubmedqa_pqa_labeled_train.jsonl",
            seed=args.seed,
            force_overwrite=args.force_overwrite,
        )

    print("Download step complete.")


if __name__ == "__main__":
    main()
