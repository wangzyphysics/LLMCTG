#!/usr/bin/env python3
"""LLM中文文本生成系统一键功能测试。

默认使用项目在 Linux 服务器上的预设路径。每项测试执行前都会显示测试功能和
预期结果；所有产物写入带时间戳的新目录，不覆盖既有测试结果。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable


DEFAULT_PROJECT_ROOT = Path("/home/xxx/workplace/xxx/llmctg")
DEFAULT_MODEL_PATH = Path("/home/xxx/workplace/xxx/Qwen3-1.7B")


class TestFailure(RuntimeError):
    pass


class Runner:
    def __init__(self, project_root: Path, model_path: Path, output_root: Path, device: str):
        self.project_root = project_root
        self.model_path = model_path
        self.output_root = output_root
        self.device = device
        self.results: list[dict[str, str]] = []
        self.env = os.environ.copy()
        if device.startswith("cuda:"):
            # 对外只暴露选中的物理卡；进程内统一使用 cuda:0，避免 Trainer 自动多卡。
            self.env["CUDA_VISIBLE_DEVICES"] = device.split(":", 1)[1]
            self.process_device = "cuda:0"
        else:
            self.process_device = device

    def announce(self, number: int, name: str, expected: str) -> None:
        print("\n" + "=" * 78)
        print(f"测试 {number}: {name}")
        print(f"运行功能: {name}")
        print(f"预期结果: {expected}")
        print("=" * 78, flush=True)

    def command(self, *arguments: str, accepted_codes: set[int] | None = None) -> None:
        command = [sys.executable, "-m", "llmctg", *map(str, arguments)]
        print("执行命令:", " ".join(command), flush=True)
        completed = subprocess.run(
            command,
            cwd=self.project_root,
            env=self.env,
            text=True,
        )
        accepted = accepted_codes or {0}
        if completed.returncode not in accepted:
            raise TestFailure(f"命令退出码为 {completed.returncode}，预期为 {sorted(accepted)}")

    @staticmethod
    def require(path: Path, description: str) -> None:
        if not path.exists():
            raise TestFailure(f"未生成{description}: {path}")

    @staticmethod
    def require_json(path: Path) -> dict:
        Runner.require(path, "JSON 文件")
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)

    @staticmethod
    def require_jsonl(path: Path, minimum: int = 1) -> list[dict]:
        Runner.require(path, "JSONL 文件")
        with path.open("r", encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream if line.strip()]
        if len(records) < minimum:
            raise TestFailure(f"{path} 只有 {len(records)} 条记录，预期至少 {minimum} 条")
        return records

    def execute(self, number: int, name: str, expected: str, function: Callable[[], None]) -> None:
        self.announce(number, name, expected)
        try:
            function()
        except Exception as error:
            self.results.append({"test": name, "status": "FAIL", "detail": str(error)})
            print(f"[失败] {error}", flush=True)
        else:
            self.results.append({"test": name, "status": "PASS", "detail": expected})
            print(f"[通过] {expected}", flush=True)

    def test_version(self) -> None:
        self.command("--version")

    def test_init_config(self) -> None:
        target = self.output_root / "llmctg.json"
        self.command("init-config", "--output", target)
        payload = self.require_json(target)
        if "generation" not in payload or "evaluation" not in payload:
            raise TestFailure("配置文件缺少 generation 或 evaluation")

    def test_prepare_data(self) -> None:
        source = self.project_root / "test_data" / "llmctg_smoke_train.txt"
        target = self.output_root / "prepared_train.jsonl"
        self.command("prepare-data", "--input", source, "--output", target)
        self.require_jsonl(target, minimum=12)

    def test_template_generate(self) -> None:
        target = self.output_root / "template_generation.jsonl"
        self.command(
            "generate", "--backend", "template", "--topic", "城市河流",
            "--level", "junior", "--keywords", "河流,生态,保护",
            "--count", "1", "--seed", "2026", "--output", target,
        )
        records = self.require_jsonl(target)
        if records[0].get("backend") != "template":
            raise TestFailure("生成结果的 backend 不是 template")

    def test_evaluate(self) -> None:
        target = self.output_root / "evaluation.json"
        text = (
            "城市河流为植物和动物提供生活空间，也能调节局部气候。"
            "保护河流需要减少污水排放、修复河岸植被，并鼓励居民节约用水。"
        )
        self.command(
            "evaluate", "--text", text, "--level", "junior", "--output", target,
            accepted_codes={0, 1},
        )
        payload = self.require_json(target)
        if "metrics" not in payload or "statistics" not in payload:
            raise TestFailure("评估结果缺少 metrics 或 statistics")

    def test_batch(self) -> None:
        output = self.output_root / "batch"
        self.command(
            "batch", "--backend", "template",
            "--input", self.project_root / "examples" / "tasks.jsonl",
            "--output", output, "--no-resume",
        )
        self.require_jsonl(output / "articles.jsonl", minimum=3)
        self.require(output / "summary.json", "批处理摘要")
        self.require(output / "summary.csv", "批处理 CSV")
        self.require(output / "report.html", "批处理 HTML 报告")

    def test_demo(self) -> None:
        output = self.output_root / "demo"
        self.command("demo", "--output", output)
        self.require_jsonl(output / "articles.jsonl", minimum=3)
        self.require(output / "report.html", "演示 HTML 报告")

    def test_base_model_generate(self) -> None:
        target = self.output_root / "qwen3_base_generation.jsonl"
        self.command(
            "generate", "--backend", "transformers", "--model-path", self.model_path,
            "--device", self.process_device, "--topic", "城市河流与生态保护",
            "--level", "junior",
            "--instruction", "说明城市河流的生态价值、主要污染来源和保护方法",
            "--keywords", "河流,生态,污染,保护", "--count", "1", "--seed", "2026",
            "--output", target,
        )
        records = self.require_jsonl(target)
        if not records[0].get("content", "").strip():
            raise TestFailure("本地模型生成正文为空")

    def test_train(self) -> None:
        dataset = self.output_root / "prepared_train.jsonl"
        adapter = self.output_root / "qwen3-1.7b-lora-smoke"
        self.command(
            "train", "--model-path", self.model_path, "--dataset", dataset,
            "--output", adapter, "--epochs", "1", "--batch-size", "1",
            "--max-length", "256", "--device", self.process_device,
        )
        self.require(adapter / "adapter_config.json", "LoRA 配置")
        self.require(adapter / "adapter_model.safetensors", "LoRA 权重")

    def test_lora_generate(self) -> None:
        adapter = self.output_root / "qwen3-1.7b-lora-smoke"
        target = self.output_root / "qwen3_lora_generation.jsonl"
        self.command(
            "generate", "--backend", "transformers", "--model-path", self.model_path,
            "--lora-path", adapter, "--device", self.process_device,
            "--topic", "城市河流与生态保护", "--level", "junior",
            "--instruction", "说明城市河流的生态价值、主要污染来源和保护方法",
            "--keywords", "河流,生态,污染,保护", "--count", "1", "--seed", "2026",
            "--output", target,
        )
        records = self.require_jsonl(target)
        if not records[0].get("content", "").strip():
            raise TestFailure("LoRA 模型生成正文为空")

    def write_summary(self) -> Path:
        summary = self.output_root / "test_summary.json"
        summary.write_text(
            json.dumps(self.results, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return summary


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LLM中文文本生成系统一键功能测试")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--device", default="cuda:0", help="cpu、cuda 或 cuda:N")
    parser.add_argument("--skip-llm", action="store_true", help="跳过本地模型、训练及 LoRA 测试")
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    project_root = args.project_root.resolve()
    model_path = args.model_path.resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_root = project_root / "test_output" / f"one_click_{stamp}"
    output_root.mkdir(parents=True, exist_ok=False)

    print("LLM中文文本生成系统——一键功能测试")
    print(f"项目路径: {project_root}")
    print(f"模型路径: {model_path}")
    print(f"输出路径: {output_root}")
    print(f"计算设备: {args.device}")

    runner = Runner(project_root, model_path, output_root, args.device)
    tests: list[tuple[str, str, Callable[[], None]]] = [
        ("版本与命令入口", "输出 llmctg 版本号，退出码为 0。", runner.test_version),
        ("默认配置生成", "生成可解析且包含 generation、evaluation 的 JSON 配置。", runner.test_init_config),
        ("训练数据转换", "把标注文本转换成至少 12 条 JSONL 训练样本。", runner.test_prepare_data),
        ("模板文本生成", "生成 1 条正文且 backend 为 template。", runner.test_template_generate),
        ("文本质量评估", "生成包含统计指标和质量指标的 JSON；是否及格不影响功能判定。", runner.test_evaluate),
        ("批量任务处理", "处理 3 条任务并生成 JSONL、JSON、CSV 和 HTML 报告。", runner.test_batch),
        ("完整离线演示", "生成 3 篇示例文章及汇总报告。", runner.test_demo),
    ]
    if not args.skip_llm:
        tests.extend([
            ("本地基础模型生成", "Qwen3 基础模型生成一条非空中文文本。", runner.test_base_model_generate),
            ("LoRA 冒烟微调", "完成 1 轮训练并保存 adapter_config.json 和适配器权重。", runner.test_train),
            ("LoRA 适配器生成", "加载刚训练的适配器并生成一条非空中文文本。", runner.test_lora_generate),
        ])

    for number, (name, expected, function) in enumerate(tests, 1):
        runner.execute(number, name, expected, function)

    summary = runner.write_summary()
    failed = [item for item in runner.results if item["status"] == "FAIL"]
    print("\n" + "=" * 78)
    print(f"测试完成：通过 {len(runner.results) - len(failed)}，失败 {len(failed)}")
    print(f"汇总文件：{summary}")
    print(f"全部产物：{output_root}")
    if failed:
        print("失败项目：" + "、".join(item["test"] for item in failed))
        return 1
    print("预期结果：所有测试均显示 PASS，LoRA 适配器及生成结果均已保存。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
