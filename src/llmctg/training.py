from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FineTuneOptions:
    model_path: str
    dataset_path: str
    output_dir: str
    epochs: float = 3.0
    batch_size: int = 1
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    max_length: int = 1024
    lora_rank: int = 8
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    device: str = "auto"

    def validate(self) -> None:
        if not Path(self.model_path).exists():
            raise FileNotFoundError(f"基础模型目录不存在: {self.model_path}")
        if not Path(self.dataset_path).exists():
            raise FileNotFoundError(f"训练数据不存在: {self.dataset_path}")
        if self.epochs <= 0 or self.batch_size <= 0 or self.max_length < 64:
            raise ValueError("训练轮数、批量大小和最大长度必须为有效正数")


class LoraTrainer:
    """把原始微调脚本封装为显式配置、可验证的训练服务。"""

    def __init__(self, options: FineTuneOptions):
        options.validate()
        self.options = options

    def train(self) -> dict[str, Any]:
        try:
            import torch
            from datasets import Dataset
            from peft import LoraConfig, TaskType, get_peft_model
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                DataCollatorForLanguageModeling,
                Trainer,
                TrainingArguments,
            )
        except ImportError as error:
            raise RuntimeError("缺少训练依赖，请安装 torch、transformers、datasets 和 peft") from error

        device = self.options.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        tokenizer = AutoTokenizer.from_pretrained(
            self.options.model_path, trust_remote_code=False, use_fast=True
        )
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        base_model = AutoModelForCausalLM.from_pretrained(
            self.options.model_path, trust_remote_code=False, dtype=dtype
        )
        lora = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            inference_mode=False,
            r=self.options.lora_rank,
            lora_alpha=self.options.lora_alpha,
            lora_dropout=self.options.lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        )
        model = get_peft_model(base_model, lora)
        model.config.use_cache = False
        if device.startswith("cuda"):
            model.gradient_checkpointing_enable()
            model.enable_input_require_grads()
        model.to(device)

        dataset = Dataset.from_json(self.options.dataset_path)

        def tokenize(record: dict[str, Any]) -> dict[str, Any]:
            instruction = str(record.get("instruction", "")).strip()
            input_text = str(record.get("input", "")).strip()
            output_text = str(record.get("output", "")).strip()
            prompt = instruction + ("\n" + input_text if input_text else "")
            full_text = prompt + "\n" + output_text
            encoded = tokenizer(
                full_text,
                truncation=True,
                max_length=self.options.max_length,
                padding=False,
            )
            return encoded

        tokenized = dataset.map(tokenize, remove_columns=dataset.column_names)
        argument_values = {
            "output_dir": self.options.output_dir,
            "overwrite_output_dir": True,
            "num_train_epochs": self.options.epochs,
            "per_device_train_batch_size": self.options.batch_size,
            "gradient_accumulation_steps": self.options.gradient_accumulation_steps,
            "learning_rate": self.options.learning_rate,
            "fp16": device.startswith("cuda"),
            "save_strategy": "epoch",
            "save_total_limit": 2,
            "logging_steps": 10,
            "report_to": "none",
            "dataloader_num_workers": 0,
            "remove_unused_columns": False,
        }
        supported_arguments = inspect.signature(TrainingArguments.__init__).parameters
        arguments = TrainingArguments(**{
            name: value
            for name, value in argument_values.items()
            if name in supported_arguments
        })
        trainer_values = {
            "model": model,
            "args": arguments,
            "train_dataset": tokenized,
            "data_collator": DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
        }
        supported_trainer_arguments = inspect.signature(Trainer.__init__).parameters
        if "processing_class" in supported_trainer_arguments:
            trainer_values["processing_class"] = tokenizer
        elif "tokenizer" in supported_trainer_arguments:
            trainer_values["tokenizer"] = tokenizer
        trainer = Trainer(**trainer_values)
        result = trainer.train()
        model.save_pretrained(self.options.output_dir)
        tokenizer.save_pretrained(self.options.output_dir)
        return {
            "output_dir": str(Path(self.options.output_dir).resolve()),
            "train_samples": len(tokenized),
            "train_loss": float(result.training_loss),
            "global_step": int(result.global_step),
            "device": device,
        }

