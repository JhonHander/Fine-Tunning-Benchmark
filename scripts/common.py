from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

import jsonlines
import pandas as pd

SYSTEM_PROMPT = (
    "You are a helpful medical AI assistant. "
    "Provide accurate and evidence-based medical information."
)
VALID_ROLES = {"system", "user", "assistant"}
CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")
    text = CONTROL_CHARS_RE.sub("", text)

    normalized_lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(normalized_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def build_chat_example(
    user_text: str,
    assistant_text: str,
    source: str,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {"source": source}
    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ],
        "metadata": metadata,
    }


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(path, mode="w") as writer:
        for row in rows:
            writer.write(row)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with jsonlines.open(path, mode="r") as reader:
        for row in reader:
            rows.append(row)
    return rows


def parse_json_file(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("questions", "data", "examples", "items", "records"):
            maybe_list = data.get(key)
            if isinstance(maybe_list, list):
                return [x for x in maybe_list if isinstance(x, dict)]
        return [data]

    return []


def parse_jsonl_file(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with jsonlines.open(path, mode="r") as reader:
        for row in reader:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def parse_tabular_file(path: Path) -> List[Dict[str, Any]]:
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    df = pd.read_csv(path, sep=sep)
    return df.to_dict(orient="records")


def load_records_from_path(input_path: Path) -> List[Dict[str, Any]]:
    if input_path.is_file():
        files = [input_path]
    else:
        files = sorted(
            p
            for p in input_path.rglob("*")
            if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".csv", ".tsv"}
        )

    rows: List[Dict[str, Any]] = []
    for file in files:
        suffix = file.suffix.lower()
        if suffix == ".json":
            rows.extend(parse_json_file(file))
        elif suffix == ".jsonl":
            rows.extend(parse_jsonl_file(file))
        elif suffix in {".csv", ".tsv"}:
            rows.extend(parse_tabular_file(file))
    return rows


def dedupe_by_pair(examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for ex in examples:
        try:
            user_text = ex["messages"][1]["content"]
            assistant_text = ex["messages"][2]["content"]
        except (IndexError, KeyError, TypeError):
            continue
        key = (user_text, assistant_text, ex.get("metadata", {}).get("source", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ex)
    return deduped


def validate_example(example: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    messages = example.get("messages")
    metadata = example.get("metadata")

    if not isinstance(messages, list) or len(messages) == 0:
        errors.append("messages_missing_or_empty")
        return errors

    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            errors.append(f"message_{idx}_not_dict")
            continue
        role = message.get("role")
        content = message.get("content")
        if role not in VALID_ROLES:
            errors.append(f"message_{idx}_invalid_role")
        if not is_non_empty_str(content):
            errors.append(f"message_{idx}_empty_content")

    source = metadata.get("source") if isinstance(metadata, dict) else None
    if not isinstance(metadata, dict) or not is_non_empty_str(source):
        errors.append("metadata_source_missing")

    return errors


def ensure_clean_non_empty(value: Any) -> str:
    return clean_text(value)


def normalize_weight_map(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Weights must sum to a positive number.")
    return {k: v / total for k, v in weights.items()}


def find_first_non_empty(record: Dict[str, Any], keys: List[str]) -> str:
    for key in keys:
        value = record.get(key)
        if value is None:
            continue
        cleaned = clean_text(value)
        if cleaned:
            return cleaned
    return ""


def list_candidate_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    return sorted([p for p in path.rglob("*") if p.is_file()])
