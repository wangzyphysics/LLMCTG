from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import GenerationRequest


class TextGenerator(ABC):
    name = "base"

    @abstractmethod
    def generate(self, request: GenerationRequest) -> list[tuple[str, str]]:
        """返回标题、正文组成的列表。"""

    def close(self) -> None:
        """释放可选的模型资源。"""
