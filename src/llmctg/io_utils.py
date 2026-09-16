from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Iterator


class DataFormatError(ValueError):
    """输入记录无法解析时抛出。"""


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"输入文件不存在: {source}")
    with source.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise DataFormatError(f"{source} 第 {line_number} 行不是有效 JSON: {error.msg}") from error
            if not isinstance(value, dict):
                raise DataFormatError(f"{source} 第 {line_number} 行必须是 JSON 对象")
            value["_line_number"] = line_number
            yield value


def append_jsonl(path: str | Path, value: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    return target


def write_json(path: str | Path, value: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return target


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target


def existing_ids(path: str | Path, key: str = "request_id") -> set[str]:
    target = Path(path)
    if not target.exists():
        return set()
    found: set[str] = set()
    try:
        for record in read_jsonl(target):
            value = record.get(key)
            if value:
                found.add(str(value))
    except DataFormatError:
        return found
    return found
