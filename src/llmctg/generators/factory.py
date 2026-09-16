from __future__ import annotations

from ..config import GenerationConfig
from .base import TextGenerator
from .template import TemplateGenerator


def create_generator(config: GenerationConfig) -> TextGenerator:
    backend = config.backend.strip().lower()
    if backend in {"template", "demo", "offline"}:
        return TemplateGenerator()
    if backend in {"transformers", "huggingface", "local-model"}:
        from .transformers_backend import TransformersGenerator
        return TransformersGenerator(config)
    raise ValueError(f"不支持的生成后端: {config.backend}")
