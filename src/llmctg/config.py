from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GenerationConfig:
    backend: str = "template"
    model_path: str = ""
    device: str = "auto"
    lora_path: str = ""
    temperature: float = 0.9
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    max_new_tokens_primary: int = 380
    max_new_tokens_junior: int = 800
    max_new_tokens_senior: int = 1200


@dataclass(slots=True)
class EvaluationConfig:
    pass_score: float = 60.0
    excellent_score: float = 85.0
    good_score: float = 70.0
    primary_sentence_target: float = 16.0
    junior_sentence_target: float = 24.0
    senior_sentence_target: float = 34.0
    repetition_warning: float = 0.18
    english_warning: float = 0.15


@dataclass(slots=True)
class AppConfig:
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    log_level: str = "INFO"
    output_encoding: str = "utf-8"

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AppConfig":
        if not path:
            return cls()
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        with config_path.open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
        return cls(
            generation=GenerationConfig(**raw.get("generation", {})),
            evaluation=EvaluationConfig(**raw.get("evaluation", {})),
            log_level=raw.get("log_level", "INFO"),
            output_encoding=raw.get("output_encoding", "utf-8"),
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as stream:
            json.dump(asdict(self), stream, ensure_ascii=False, indent=2)
        return target

    def merge(self, values: dict[str, Any]) -> "AppConfig":
        for section, section_values in values.items():
            target = getattr(self, section, None)
            if target is None or not isinstance(section_values, dict):
                continue
            for name, value in section_values.items():
                if hasattr(target, name) and value is not None:
                    setattr(target, name, value)
        return self
