from __future__ import annotations

from pathlib import Path
from typing import Any

from ..config import GenerationConfig
from ..models import GenerationRequest, ReadingLevel
from ..text_utils import ensure_terminal_punctuation
from .base import TextGenerator


class TransformersGenerator(TextGenerator):
    """惰性加载本地 Hugging Face 模型的可选生成后端。"""

    name = "transformers"

    def __init__(self, config: GenerationConfig):
        if not config.model_path:
            raise ValueError("使用 transformers 后端时必须指定 model_path")
        self.config = config
        self._torch: Any = None
        self._tokenizer: Any = None
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError("缺少模型依赖，请执行 pip install -e .[llm]") from error
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path, trust_remote_code=False, use_fast=True
        )
        device = self.config.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if str(device).startswith("cuda") else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            self.config.model_path, trust_remote_code=False, dtype=dtype
        )
        if self.config.lora_path:
            adapter_path = Path(self.config.lora_path)
            if not adapter_path.is_dir():
                raise FileNotFoundError(f"LoRA 适配器目录不存在: {adapter_path}")
            if not (adapter_path / "adapter_config.json").is_file():
                raise FileNotFoundError(f"LoRA 适配器配置不存在: {adapter_path / 'adapter_config.json'}")
            try:
                from peft import PeftModel
            except ImportError as error:
                raise RuntimeError("加载 LoRA 适配器需要 peft，请执行 pip install -e .[llm]") from error
            model = PeftModel.from_pretrained(
                model, str(adapter_path), is_trainable=False
            )
        self._model = model.to(device)
        self._model.eval()
        if self._tokenizer.pad_token_id is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

    def generate(self, request: GenerationRequest) -> list[tuple[str, str]]:
        request.validate()
        self._load()
        return [self._generate_one(request, index) for index in range(request.count)]

    def _generate_one(self, request: GenerationRequest, index: int) -> tuple[str, str]:
        prompt = self._build_prompt(request)
        device = next(self._model.parameters()).device
        encoded = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)
        encoded = {key: value.to(device) for key, value in encoded.items()}
        maximums = {
            ReadingLevel.PRIMARY: self.config.max_new_tokens_primary,
            ReadingLevel.JUNIOR: self.config.max_new_tokens_junior,
            ReadingLevel.SENIOR: self.config.max_new_tokens_senior,
        }
        if request.seed is not None:
            seed = request.seed + index
            self._torch.manual_seed(seed)
            if self._torch.cuda.is_available():
                self._torch.cuda.manual_seed_all(seed)
        with self._torch.inference_mode():
            output = self._model.generate(
                **encoded,
                do_sample=True,
                max_new_tokens=maximums[request.level],
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repetition_penalty=self.config.repetition_penalty,
                pad_token_id=self._tokenizer.pad_token_id,
                eos_token_id=self._tokenizer.eos_token_id,
            )
        new_tokens = output[0, encoded["input_ids"].shape[-1]:]
        content = self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        title = f"{request.topic}分级阅读材料"
        return title, ensure_terminal_punctuation(content)

    @staticmethod
    def _build_prompt(request: GenerationRequest) -> str:
        keywords = "、".join(request.keywords) if request.keywords else "无指定关键词"
        extra = request.instruction.strip() or "内容准确、结构完整、表达自然"
        return (
            f"请围绕“{request.topic}”创作一篇适合{request.level.chinese_name}学生阅读的中文文章。\n"
            f"关键词：{keywords}\n要求：{extra}\n只输出文章正文，不要解释创作过程。\n正文："
        )

    def close(self) -> None:
        self._model = None
        self._tokenizer = None
        if self._torch is not None and self._torch.cuda.is_available():
            self._torch.cuda.empty_cache()

