from pathlib import Path

import pytest

from llmctg.cli import build_parser
from llmctg.config import AppConfig, GenerationConfig
from llmctg.generators.transformers_backend import TransformersGenerator


def test_generate_parser_accepts_lora_path():
    args = build_parser().parse_args([
        "generate",
        "--backend", "transformers",
        "--model-path", "/models/qwen",
        "--lora-path", "/adapters/chinese",
        "--topic", "城市河流",
    ])
    assert args.lora_path == "/adapters/chinese"


def test_config_accepts_lora_path(tmp_path: Path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        '{"generation":{"backend":"transformers","model_path":"/model",'
        '"lora_path":"/adapter"}}',
        encoding="utf-8",
    )
    assert AppConfig.load(config_file).generation.lora_path == "/adapter"


def test_missing_lora_directory_has_clear_error(monkeypatch, tmp_path: Path):
    generator = TransformersGenerator(GenerationConfig(
        backend="transformers",
        model_path=str(tmp_path / "model"),
        lora_path=str(tmp_path / "missing-adapter"),
        device="cpu",
    ))

    class FakeTorch:
        float16 = "float16"
        float32 = "float32"

        class cuda:
            @staticmethod
            def is_available():
                return False

    class FakeTokenizer:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return object()

    class FakeModelFactory:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            return object()

    monkeypatch.setitem(__import__("sys").modules, "torch", FakeTorch)
    fake_transformers = type("FakeTransformers", (), {
        "AutoModelForCausalLM": FakeModelFactory,
        "AutoTokenizer": FakeTokenizer,
    })
    monkeypatch.setitem(__import__("sys").modules, "transformers", fake_transformers)

