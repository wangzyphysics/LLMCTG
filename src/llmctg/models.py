from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ReadingLevel(str, Enum):
    PRIMARY = "primary"
    JUNIOR = "junior"
    SENIOR = "senior"

    @property
    def chinese_name(self) -> str:
        return {self.PRIMARY: "小学", self.JUNIOR: "初中", self.SENIOR: "高中"}[self]

    @property
    def numeric_label(self) -> int:
        return {self.PRIMARY: 0, self.JUNIOR: 1, self.SENIOR: 2}[self]

    @classmethod
    def parse(cls, value: str | int | "ReadingLevel") -> "ReadingLevel":
        if isinstance(value, cls):
            return value
        aliases = {
            "0": cls.PRIMARY, "小学": cls.PRIMARY, "小学生": cls.PRIMARY,
            "primary": cls.PRIMARY,
            "1": cls.JUNIOR, "初中": cls.JUNIOR, "初中生": cls.JUNIOR,
            "junior": cls.JUNIOR,
            "2": cls.SENIOR, "高中": cls.SENIOR, "高中生": cls.SENIOR,
            "senior": cls.SENIOR,
        }
        key = str(value).strip().lower()
        if key not in aliases:
            raise ValueError(f"不支持的阅读等级: {value}")
        return aliases[key]


@dataclass(slots=True)
class GenerationRequest:
    topic: str
    level: ReadingLevel = ReadingLevel.JUNIOR
    instruction: str = ""
    keywords: list[str] = field(default_factory=list)
    count: int = 1
    seed: int | None = None

    def validate(self) -> None:
        self.topic = self.topic.strip()
        if not self.topic:
            raise ValueError("主题不能为空")
        if not 1 <= self.count <= 20:
            raise ValueError("单次生成数量必须在 1 到 20 之间")
        self.level = ReadingLevel.parse(self.level)
        self.keywords = [str(item).strip() for item in self.keywords if str(item).strip()]


@dataclass(slots=True)
class TextStatistics:
    characters: int
    chinese_characters: int
    sentences: int
    paragraphs: int
    average_sentence_length: float
    max_sentence_length: int
    unique_character_ratio: float
    punctuation_ratio: float


@dataclass(slots=True)
class QualityMetrics:
    repetition_rate: float
    english_ratio: float
    uncommon_character_ratio: float
    structure_score: float
    length_score: float
    level_score: float
    overall_score: float


@dataclass(slots=True)
class EvaluationResult:
    target_level: ReadingLevel
    predicted_level: ReadingLevel
    quality_grade: str
    passed: bool
    statistics: TextStatistics
    metrics: QualityMetrics
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["target_level"] = self.target_level.value
        data["predicted_level"] = self.predicted_level.value
        return data


@dataclass(slots=True)
class GeneratedArticle:
    request_id: str
    topic: str
    level: ReadingLevel
    title: str
    content: str
    backend: str
    created_at: str
    evaluation: EvaluationResult | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["level"] = self.level.value
        if self.evaluation:
            data["evaluation"] = self.evaluation.to_dict()
        return data
