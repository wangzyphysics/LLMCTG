from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from pathlib import Path

CHINESE_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？!?；;])")
WHITESPACE_PATTERN = re.compile(r"[ \t\r\f\v]+")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [WHITESPACE_PATTERN.sub(" ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).strip()


def ensure_terminal_punctuation(text: str) -> str:
    text = normalize_text(text)
    if text and text[-1] not in "。！？!?…\"”’」』）)":
        return text + "。"
    return text


def split_sentences(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    parts = SENTENCE_SPLIT_PATTERN.split(normalized.replace("\n", ""))
    return [item.strip() for item in parts if item.strip()]


def split_paragraphs(text: str) -> list[str]:
    return [line.strip() for line in normalize_text(text).split("\n") if line.strip()]


def chinese_characters(text: str) -> list[str]:
    return CHINESE_PATTERN.findall(text)


def character_ngrams(text: str, size: int = 4) -> list[str]:
    chars = chinese_characters(text)
    if size <= 0:
        raise ValueError("n-gram 长度必须为正整数")
    return ["".join(chars[index:index + size]) for index in range(max(0, len(chars) - size + 1))]


def repetition_rate(text: str, size: int = 4) -> float:
    grams = character_ngrams(text, size=size)
    if not grams:
        return 0.0
    counts = Counter(grams)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(grams)


def stable_id(*values: object, length: int = 16) -> str:
    joined = "\x1f".join(str(value) for value in values)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:length]


def safe_filename(value: str, fallback: str = "output") -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", normalize_text(value))
    cleaned = cleaned.strip(" ._")
    return (cleaned or fallback)[:80]


def read_text(path: str | Path) -> str:
    with Path(path).open("r", encoding="utf-8-sig") as stream:
        return stream.read()


def write_text(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    return target
