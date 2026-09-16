from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .models import ReadingLevel


@dataclass(slots=True)
class TrainingSample:
    instruction: str
    input: str
    output: str
    level: ReadingLevel

    def to_dict(self) -> dict[str, str]:
        return {
            "instruction": self.instruction,
            "input": self.input,
            "output": self.output,
            "level": self.level.value,
        }


def parse_labeled_text(path: str | Path) -> Iterator[TrainingSample]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                text, raw_level = stripped.rsplit("\t", 1)
            except ValueError as error:
                raise ValueError(f"{source} 第 {line_number} 行缺少制表符和等级标签") from error
            level = ReadingLevel.parse(raw_level)
            text = text.strip()
            if not text:
                raise ValueError(f"{source} 第 {line_number} 行正文为空")
            yield TrainingSample(
                instruction=f"请生成一段适合{level.chinese_name}学生阅读的中文内容。",
                input="",
                output=text,
                level=level,
            )


def convert_labeled_text(input_path: str | Path, output_path: str | Path) -> int:
    samples = list(parse_labeled_text(input_path))
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        for sample in samples:
            stream.write(json.dumps(sample.to_dict(), ensure_ascii=False) + "\n")
    return len(samples)
