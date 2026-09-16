# LLM中文文本生成系统V1.0源程序鉴别材料

本文档收录当前 LLMCTG 目录中的核心程序、命令脚本、配置和自动化测试源码。
生成文档的构建脚本不纳入鉴别材料。
共收录 30 个文件，约 2111 行源代码。


## 文件清单

- `.gitignore`
- `pyproject.toml`
- `scripts/export_docs_markdown.py`
- `scripts/one_click_test.py`
- `scripts/run_demo.ps1`
- `scripts/run_demo.sh`
- `scripts/run_tests.ps1`
- `src/llmctg/__init__.py`
- `src/llmctg/__main__.py`
- `src/llmctg/cli.py`
- `src/llmctg/config.py`
- `src/llmctg/dataset.py`
- `src/llmctg/evaluator.py`
- `src/llmctg/generators/__init__.py`
- `src/llmctg/generators/base.py`
- `src/llmctg/generators/factory.py`
- `src/llmctg/generators/template.py`
- `src/llmctg/generators/transformers_backend.py`
- `src/llmctg/io_utils.py`
- `src/llmctg/logging_utils.py`
- `src/llmctg/models.py`
- `src/llmctg/pipeline.py`
- `src/llmctg/reporting.py`
- `src/llmctg/text_utils.py`
- `src/llmctg/training.py`
- `tests/test_evaluator.py`
- `tests/test_lora_generation.py`
- `tests/test_models.py`
- `tests/test_pipeline.py`
- `tests/test_text_utils.py`

## .gitignore

```text
# Python bytecode and caches
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Packaging and virtual environments
*.egg-info/
build/
dist/
.venv/
venv/
env/

# Jupyter temporary files
.ipynb_checkpoints/

# IDE and operating-system files
.idea/
.vscode/
.DS_Store
Thumbs.db

# Runtime logs and generated test outputs
*.log
test_output/
output/*
!output/.gitkeep
!output/demo/
!output/demo/.gitkeep

# Local configuration and environment secrets
.env
.env.*
llmctg.local.json

# Local model weights and training checkpoints
models/
checkpoints/
checkpoint-*/
*.bin
*.pt
*.pth
*.ckpt
*.safetensors

# Internal document rendering and QA intermediates
qa/
deliverables/*.pdf
~$*.docx
```

## pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "llmctg"
version = "1.0.0"
description = "LLM Chinese Text Generator"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "Proprietary"}
dependencies = []

[project.optional-dependencies]
llm = [
    "torch==2.6.0",
    "transformers>=4.51,<5",
    "peft>=0.10,<1",
    "datasets>=2.18,<5",
    "accelerate>=0.26,<2",
]
dev = ["pytest>=8.0"]

[project.scripts]
llmctg = "llmctg.cli:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

## scripts/export_docs_markdown.py

```python
"""Export the generated manual and current source tree as Markdown deliverables."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph

from build_copyright_docs import DELIVERY, SOFTWARE_NAME, VERSION, source_files

ROOT = Path(__file__).resolve().parents[1]


def iter_blocks(parent):
    parent_element = parent.element.body if isinstance(parent, DocumentObject) else parent._tc
    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def escape_cell(text: str) -> str:
    return "<br>".join(part.strip() for part in text.splitlines()).replace("|", "\\|")


def paragraph_is_code(paragraph: Paragraph) -> bool:
    visible_runs = [run for run in paragraph.runs if run.text]
    return bool(visible_runs) and all(run.font.name == "Consolas" for run in visible_runs)


def manual_to_markdown(source: Path, target: Path) -> None:
    document = Document(source)
    output: list[str] = []
    code_lines: list[str] = []

    def flush_code() -> None:
        if code_lines:
            output.extend(["```bash", *code_lines, "```", ""])
            code_lines.clear()

    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if not text:
                flush_code()
                continue
            if paragraph_is_code(block):
                code_lines.append(block.text)
                continue
            flush_code()
            style = block.style.name if block.style else ""
            if style == "Title":
                output.extend([f"# {text}", ""])
            elif style.startswith("Heading "):
                level = int(style.rsplit(" ", 1)[1])
                output.extend([f"{'#' * (level + 1)} {text}", ""])
            elif style.startswith("List Bullet"):
                output.extend([f"- {text}", ""])
            else:
                output.extend([text, ""])
        else:
            flush_code()
            rows = [[escape_cell(cell.text) for cell in row.cells] for row in block.rows]
            if not rows:
                continue
            output.append("| " + " | ".join(rows[0]) + " |")
            output.append("| " + " | ".join("---" for _ in rows[0]) + " |")
            for row in rows[1:]:
                output.append("| " + " | ".join(row) + " |")
            output.append("")
    flush_code()
    target.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


def source_to_markdown(target: Path) -> None:
    files = source_files()
    total_lines = 0
    sections: list[str] = [
        f"# {SOFTWARE_NAME}{VERSION}源程序鉴别材料",
        "",
        "本文档收录当前 LLMCTG 目录中的核心程序、命令脚本、配置和自动化测试源码。",
        "生成文档的构建脚本不纳入鉴别材料。",
        "",
        "## 文件清单",
        "",
    ]
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        sections.append(f"- `{relative}`")
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        lines = content.splitlines()
        total_lines += len(lines)
        language = {
            ".py": "python", ".ps1": "powershell", ".sh": "bash",
            ".toml": "toml", ".json": "json",
        }.get(path.suffix.lower(), "text")
        sections.extend([
            "",
            f"## {relative}",
            "",
            f"```{language}",
            content.rstrip(),
            "```",
        ])
    sections[4:4] = [f"共收录 {len(files)} 个文件，约 {total_lines} 行源代码。", ""]
    target.write_text("\n".join(sections).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    DELIVERY.mkdir(parents=True, exist_ok=True)
    manual_docx = DELIVERY / f"{SOFTWARE_NAME}{VERSION}用户操作手册.docx"
    manual_md = DELIVERY / f"{SOFTWARE_NAME}{VERSION}用户操作手册.md"
    source_md = DELIVERY / f"{SOFTWARE_NAME}{VERSION}源程序鉴别材料.md"
    manual_to_markdown(manual_docx, manual_md)
    source_to_markdown(source_md)
    print(manual_md)
    print(source_md)


if __name__ == "__main__":
    main()
```

## scripts/one_click_test.py

```python
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
```

## scripts/run_demo.ps1

```powershell
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
python -m llmctg demo --output (Join-Path $projectRoot "output\demo")
```

## scripts/run_demo.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT/src"
python -m llmctg demo --output "$PROJECT_ROOT/output/demo"
```

## scripts/run_tests.ps1

```powershell
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
python -m pytest (Join-Path $projectRoot "tests") -q
```

## src/llmctg/__init__.py

```python
"""LLM中文文本生成系统。"""

from .models import ReadingLevel, GenerationRequest, GeneratedArticle, EvaluationResult

__all__ = ["ReadingLevel", "GenerationRequest", "GeneratedArticle", "EvaluationResult"]
__version__ = "1.0.0"
```

## src/llmctg/__main__.py

```python
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

## src/llmctg/cli.py

```python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .config import AppConfig
from .dataset import convert_labeled_text
from .io_utils import append_jsonl, write_json
from .logging_utils import configure_logging
from .models import GenerationRequest, ReadingLevel
from .pipeline import LLMCTGApplication
from .reporting import build_summary, write_html_report, write_summary_csv
from .text_utils import read_text
from .training import FineTuneOptions, LoraTrainer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="llmctg",
        description="LLM中文文本生成系统",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", help="JSON 配置文件路径")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成并评估阅读材料")
    _add_generation_arguments(generate)
    generate.add_argument("--output", help="输出 JSONL 文件，省略时打印到终端")

    evaluate = subparsers.add_parser("evaluate", help="评估已有文本")
    evaluate_source = evaluate.add_mutually_exclusive_group(required=True)
    evaluate_source.add_argument("--text", help="直接传入文本")
    evaluate_source.add_argument("--input", help="UTF-8 文本文件")
    evaluate.add_argument("--level", default="junior", help="目标等级")
    evaluate.add_argument("--output", help="输出 JSON 文件")

    batch = subparsers.add_parser("batch", help="执行 JSONL 批量任务")
    batch.add_argument("--input", required=True, help="任务 JSONL 文件")
    batch.add_argument("--output", required=True, help="结果目录")
    batch.add_argument("--no-resume", action="store_true", help="不读取已有结果的任务编号")
    _add_backend_arguments(batch)

    demo = subparsers.add_parser("demo", help="运行无需模型的完整演示")
    demo.add_argument("--output", default="output/demo", help="演示输出目录")

    init = subparsers.add_parser("init-config", help="生成默认配置文件")
    init.add_argument("--output", default="llmctg.json", help="配置文件路径")

    prepare = subparsers.add_parser("prepare-data", help="把制表符标注文本转换为训练 JSONL")
    prepare.add_argument("--input", required=True, help="每行格式为 正文 TAB 等级")
    prepare.add_argument("--output", required=True, help="训练 JSONL 输出路径")

    train = subparsers.add_parser("train", help="使用本地模型执行 LoRA 微调")
    train.add_argument("--model-path", required=True)
    train.add_argument("--dataset", required=True)
    train.add_argument("--output", required=True)
    train.add_argument("--epochs", type=float, default=3.0)
    train.add_argument("--batch-size", type=int, default=1)
    train.add_argument("--max-length", type=int, default=1024)
    train.add_argument("--device", default="auto")
    return parser


def _add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--topic", required=True, help="文章主题")
    parser.add_argument("--level", default="junior", help="primary、junior、senior 或中文等级")
    parser.add_argument("--instruction", default="", help="额外创作要求")
    parser.add_argument("--keywords", default="", help="用逗号分隔的关键词")
    parser.add_argument("--count", type=int, default=1, help="生成数量，1 到 20")
    parser.add_argument("--seed", type=int, help="随机种子")
    _add_backend_arguments(parser)


def _add_backend_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--backend", choices=["template", "transformers"], help="生成后端")
    parser.add_argument("--model-path", help="本地模型目录")
    parser.add_argument("--lora-path", help="LoRA 适配器目录，仅用于 transformers 后端")
    parser.add_argument("--device", help="auto、cpu、cuda 或 cuda:N")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = AppConfig.load(args.config)
        if args.log_level:
            config.log_level = args.log_level
        _apply_backend_arguments(config, args)
        configure_logging(config.log_level)
        if args.command == "init-config":
            path = config.save(args.output)
            print(f"已生成配置文件: {path}")
            return 0
        if args.command == "prepare-data":
            count = convert_labeled_text(args.input, args.output)
            print(f"数据转换完成，共 {count} 条: {args.output}")
            return 0
        if args.command == "train":
            result = LoraTrainer(FineTuneOptions(
                model_path=args.model_path,
                dataset_path=args.dataset,
                output_dir=args.output,
                epochs=args.epochs,
                batch_size=args.batch_size,
                max_length=args.max_length,
                device=args.device,
            )).train()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "demo":
            return _run_demo(config, args)
        with LLMCTGApplication(config) as studio:
            if args.command == "generate":
                return _run_generate(studio, args)
            if args.command == "evaluate":
                return _run_evaluate(studio, args)
            if args.command == "batch":
                summary = studio.batch(args.input, args.output, resume=not args.no_resume)
                print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))
                return 0 if summary.processing_errors == 0 else 2
        parser.error("未知命令")
    except (ValueError, FileNotFoundError, RuntimeError) as error:
        print(f"错误: {error}", file=sys.stderr)
        return 2
    return 0


def _apply_backend_arguments(config: AppConfig, args: argparse.Namespace) -> None:
    for name in ("backend", "model_path", "lora_path", "device"):
        value = getattr(args, name, None)
        if value:
            setattr(config.generation, name, value)


def _run_generate(studio: LLMCTGApplication, args: argparse.Namespace) -> int:
    keywords = [item.strip() for item in args.keywords.replace("，", ",").split(",") if item.strip()]
    request = GenerationRequest(
        topic=args.topic,
        level=ReadingLevel.parse(args.level),
        instruction=args.instruction,
        keywords=keywords,
        count=args.count,
        seed=args.seed,
    )
    articles = studio.generate(request)
    for article in articles:
        if args.output:
            append_jsonl(args.output, article.to_dict())
        else:
            print(json.dumps(article.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _run_evaluate(studio: LLMCTGApplication, args: argparse.Namespace) -> int:
    text = args.text if args.text is not None else read_text(args.input)
    result = studio.evaluate(text, ReadingLevel.parse(args.level))
    payload = result.to_dict()
    if args.output:
        write_json(args.output, payload)
        print(f"评估结果已保存: {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.passed else 1


def _run_demo(config: AppConfig, args: argparse.Namespace) -> int:
    config.generation.backend = "template"
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    articles = []
    with LLMCTGApplication(config) as studio:
        for index, (topic, level) in enumerate([
            ("四季的变化", ReadingLevel.PRIMARY),
            ("城市里的河流", ReadingLevel.JUNIOR),
            ("人工智能与学习", ReadingLevel.SENIOR),
        ]):
            request = GenerationRequest(topic=topic, level=level, count=1, seed=2026 + index)
            generated = studio.generate(request)
            articles.extend(generated)
            append_jsonl(output / "articles.jsonl", generated[0].to_dict())
    summary = build_summary(articles)
    write_json(output / "summary.json", summary.to_dict())
    write_summary_csv(output / "summary.csv", articles)
    write_html_report(output / "report.html", articles, summary)
    print(f"演示完成，结果目录: {output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## src/llmctg/config.py

```python
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
```

## src/llmctg/dataset.py

```python
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
```

## src/llmctg/evaluator.py

```python
from __future__ import annotations

import math
import re
from collections import Counter

from .config import EvaluationConfig
from .models import EvaluationResult, QualityMetrics, ReadingLevel, TextStatistics
from .text_utils import chinese_characters, normalize_text, repetition_rate, split_paragraphs, split_sentences

COMMON_CHARACTERS = set(
    "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指几九区强放决西被干做必战先回则任取据处理世车更斗百给名真论条形"
)
PUNCTUATION = set("，。！？；：、,.!?;:‘’“”()（）《》〈〉—…-\n")


class ReadabilityEvaluator:
    def __init__(self, config: EvaluationConfig | None = None):
        self.config = config or EvaluationConfig()

    def evaluate(self, text: str, target_level: ReadingLevel | str | int) -> EvaluationResult:
        target = ReadingLevel.parse(target_level)
        normalized = normalize_text(text)
        statistics = self._statistics(normalized)
        predicted = self._predict_level(statistics, normalized)
        metrics = self._metrics(normalized, target, predicted, statistics)
        warnings, suggestions = self._advice(normalized, target, statistics, metrics)
        grade = self._grade(metrics.overall_score)
        passed = metrics.overall_score >= self.config.pass_score and len(normalized) > 0
        return EvaluationResult(
            target_level=target,
            predicted_level=predicted,
            quality_grade=grade,
            passed=passed,
            statistics=statistics,
            metrics=metrics,
            warnings=warnings,
            suggestions=suggestions,
        )

    def _statistics(self, text: str) -> TextStatistics:
        chars = chinese_characters(text)
        sentences = split_sentences(text)
        paragraphs = split_paragraphs(text)
        lengths = [len(chinese_characters(item)) for item in sentences]
        unique_ratio = len(set(chars)) / len(chars) if chars else 0.0
        punctuation_count = sum(1 for char in text if char in PUNCTUATION)
        return TextStatistics(
            characters=len(text.replace("\n", "")),
            chinese_characters=len(chars),
            sentences=len(sentences),
            paragraphs=len(paragraphs),
            average_sentence_length=sum(lengths) / len(lengths) if lengths else 0.0,
            max_sentence_length=max(lengths, default=0),
            unique_character_ratio=round(unique_ratio, 4),
            punctuation_ratio=round(punctuation_count / len(text), 4) if text else 0.0,
        )

    def _predict_level(self, stats: TextStatistics, text: str) -> ReadingLevel:
        rare_ratio = self._uncommon_ratio(text)
        complexity = stats.average_sentence_length + rare_ratio * 55 + max(0, stats.max_sentence_length - 30) * 0.12
        if complexity < 20:
            return ReadingLevel.PRIMARY
        if complexity < 31:
            return ReadingLevel.JUNIOR
        return ReadingLevel.SENIOR

    def _metrics(
        self,
        text: str,
        target: ReadingLevel,
        predicted: ReadingLevel,
        stats: TextStatistics,
    ) -> QualityMetrics:
        repeat = repetition_rate(text, size=4)
        english_count = sum(1 for char in text if "a" <= char.lower() <= "z")
        english = english_count / max(1, len(text))
        uncommon = self._uncommon_ratio(text)
        structure = self._structure_score(text, stats)
        length = self._length_score(target, stats.chinese_characters)
        distance = abs(predicted.numeric_label - target.numeric_label)
        level_score = max(0.0, 100.0 - distance * 38.0)
        fluency_score = max(0.0, 100.0 - repeat * 260.0 - english * 100.0 - uncommon * 65.0)
        overall = structure * 0.20 + length * 0.20 + level_score * 0.30 + fluency_score * 0.30
        return QualityMetrics(
            repetition_rate=round(repeat, 4),
            english_ratio=round(english, 4),
            uncommon_character_ratio=round(uncommon, 4),
            structure_score=round(structure, 2),
            length_score=round(length, 2),
            level_score=round(level_score, 2),
            overall_score=round(overall, 2),
        )

    @staticmethod
    def _uncommon_ratio(text: str) -> float:
        chars = chinese_characters(text)
        if not chars:
            return 0.0
        return sum(1 for char in chars if char not in COMMON_CHARACTERS) / len(chars)

    @staticmethod
    def _structure_score(text: str, stats: TextStatistics) -> float:
        if not text:
            return 0.0
        score = 40.0
        if stats.sentences >= 3:
            score += 25
        if stats.paragraphs >= 2:
            score += 20
        if text[-1] in "。！？!?…\"”’」』）)":
            score += 10
        if re.search(r"[，、；：]", text):
            score += 5
        return min(100.0, score)

    @staticmethod
    def _length_score(level: ReadingLevel, length: int) -> float:
        targets = {
            ReadingLevel.PRIMARY: (120, 500),
            ReadingLevel.JUNIOR: (250, 1000),
            ReadingLevel.SENIOR: (400, 1800),
        }
        minimum, maximum = targets[level]
        if minimum <= length <= maximum:
            return 100.0
        if length < minimum:
            return max(0.0, length / minimum * 100.0)
        overflow = (length - maximum) / maximum
        return max(40.0, 100.0 - overflow * 70.0)

    def _grade(self, score: float) -> str:
        if score >= self.config.excellent_score:
            return "优秀"
        if score >= self.config.good_score:
            return "良好"
        if score >= self.config.pass_score:
            return "合格"
        return "待改进"

    def _advice(
        self,
        text: str,
        target: ReadingLevel,
        stats: TextStatistics,
        metrics: QualityMetrics,
    ) -> tuple[list[str], list[str]]:
        warnings: list[str] = []
        suggestions: list[str] = []
        if not text:
            return ["文本为空"], ["请输入需要评估的完整中文文本"]
        if metrics.repetition_rate > self.config.repetition_warning:
            warnings.append("连续片段重复比例偏高")
            suggestions.append("删除机械重复句，使用指代或改写衔接相近内容")
        if metrics.english_ratio > self.config.english_warning:
            warnings.append("英文字符比例偏高")
            suggestions.append("确认英文术语是否必要，并在首次出现时提供中文解释")
        sentence_targets = {
            ReadingLevel.PRIMARY: self.config.primary_sentence_target,
            ReadingLevel.JUNIOR: self.config.junior_sentence_target,
            ReadingLevel.SENIOR: self.config.senior_sentence_target,
        }
        if stats.average_sentence_length > sentence_targets[target] * 1.35:
            warnings.append("平均句长高于目标等级建议值")
            suggestions.append("拆分长句，减少连续修饰成分和多层转折")
        if stats.paragraphs < 2 and stats.chinese_characters >= 100:
            warnings.append("长文本缺少段落划分")
            suggestions.append("按引入、说明和总结划分自然段")
        if metrics.length_score < 70:
            warnings.append("文本长度与目标等级不匹配")
            suggestions.append("围绕主题补充事实、例子或总结，避免无关扩写")
        if metrics.level_score < 80:
            warnings.append("预测难度与目标阅读等级存在差异")
            direction = "降低" if stats.average_sentence_length > sentence_targets[target] else "提高"
            suggestions.append(f"通过词语解释、句式调整和信息密度控制来{direction}阅读难度")
        return warnings, list(dict.fromkeys(suggestions))
```

## src/llmctg/generators/__init__.py

```python
from .base import TextGenerator
from .factory import create_generator
from .template import TemplateGenerator

__all__ = ["TextGenerator", "TemplateGenerator", "create_generator"]
```

## src/llmctg/generators/base.py

```python
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
```

## src/llmctg/generators/factory.py

```python
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
```

## src/llmctg/generators/template.py

```python
from __future__ import annotations

import random

from ..models import GenerationRequest, ReadingLevel
from ..text_utils import ensure_terminal_punctuation
from .base import TextGenerator


class TemplateGenerator(TextGenerator):
    """用于离线演示和安装验收的确定性生成器。"""

    name = "template"

    OPENINGS = {
        ReadingLevel.PRIMARY: [
            "今天，我们一起认识{topic}。",
            "你注意过{topic}吗？它就在我们的生活里。",
            "关于{topic}，有许多有趣的小秘密。",
        ],
        ReadingLevel.JUNIOR: [
            "当我们讨论{topic}时，首先要理解它与日常生活的联系。",
            "{topic}看似熟悉，其中却包含值得追问的规律。",
            "从一个常见现象出发，我们可以逐步认识{topic}。",
        ],
        ReadingLevel.SENIOR: [
            "理解{topic}，需要同时观察事实、机制及其产生的社会影响。",
            "{topic}并非孤立现象，它由多种条件共同塑造。",
            "围绕{topic}的讨论，往往涉及科学判断与价值选择的结合。",
        ],
    }
    OBSERVATIONS = {
        ReadingLevel.PRIMARY: [
            "我们可以先看一看，再想一想它为什么会这样。",
            "仔细观察，会发现变化不是一下子发生的。",
            "把看到的事情记下来，就能发现新的线索。",
        ],
        ReadingLevel.JUNIOR: [
            "观察现象只是第一步，还要比较条件、记录变化并寻找原因。",
            "同一现象在不同环境中可能出现差异，因此结论需要证据支持。",
            "提出问题、收集资料和验证猜想，可以帮助我们避免凭感觉判断。",
        ],
        ReadingLevel.SENIOR: [
            "分析这一主题时，应区分相关关系与因果关系，并说明证据的适用范围。",
            "可靠的结论来自可重复的观察、清晰的概念和对反例的认真检验。",
            "不同尺度上的机制可能彼此影响，单一解释通常不足以覆盖全部情形。",
        ],
    }
    ACTIONS = {
        ReadingLevel.PRIMARY: [
            "我们可以从身边的小事做起，把问题写进观察本。",
            "遇到不懂的地方，可以查资料，也可以请教老师和同学。",
            "只要愿意动手试一试，知识就会变得更清楚。",
        ],
        ReadingLevel.JUNIOR: [
            "实践时可以设置一个明确目标，并用相同标准记录每次结果。",
            "阅读多种资料、核对来源，再用自己的语言概括，是有效的学习方法。",
            "如果结果与预期不同，不妨检查步骤并修正原来的假设。",
        ],
        ReadingLevel.SENIOR: [
            "进一步研究可以建立指标体系，比较不同方案的收益、成本与不确定性。",
            "面对相互冲突的材料，应检查样本、方法和论证链条，而非只看结论。",
            "将理论解释转化为可检验的问题，有助于形成审慎而开放的判断。",
        ],
    }
    CLOSINGS = {
        ReadingLevel.PRIMARY: [
            "让我们带着好奇心，继续发现{topic}的故事吧！",
            "下一次见到它时，你也许会有新的发现。",
        ],
        ReadingLevel.JUNIOR: [
            "由此可见，认识{topic}既需要知识，也需要耐心和实践。",
            "持续观察和主动求证，会让我们对{topic}形成更完整的认识。",
        ],
        ReadingLevel.SENIOR: [
            "因此，对{topic}的理解应随着证据更新，并在具体情境中接受检验。",
            "只有把事实、逻辑与责任结合起来，我们才能更稳妥地回应相关问题。",
        ],
    }

    def generate(self, request: GenerationRequest) -> list[tuple[str, str]]:
        request.validate()
        randomizer = random.Random(request.seed)
        results: list[tuple[str, str]] = []
        for index in range(request.count):
            title = self._title(request, index)
            paragraphs = self._paragraphs(request, randomizer)
            results.append((title, ensure_terminal_punctuation("\n".join(paragraphs))))
        return results

    def _title(self, request: GenerationRequest, index: int) -> str:
        suffix = "" if request.count == 1 else f"（{index + 1}）"
        names = {
            ReadingLevel.PRIMARY: f"认识{request.topic}",
            ReadingLevel.JUNIOR: f"探索{request.topic}",
            ReadingLevel.SENIOR: f"理解{request.topic}的多重视角",
        }
        return names[request.level] + suffix

    def _paragraphs(self, request: GenerationRequest, randomizer: random.Random) -> list[str]:
        context = {"topic": request.topic}
        opening = randomizer.choice(self.OPENINGS[request.level]).format(**context)
        observation = randomizer.choice(self.OBSERVATIONS[request.level]).format(**context)
        action = randomizer.choice(self.ACTIONS[request.level]).format(**context)
        closing = randomizer.choice(self.CLOSINGS[request.level]).format(**context)
        keyword_sentence = self._keyword_sentence(request)
        instruction_sentence = self._instruction_sentence(request)
        if request.level == ReadingLevel.PRIMARY:
            return [opening + keyword_sentence, observation, action, closing]
        if request.level == ReadingLevel.JUNIOR:
            return [opening + keyword_sentence, observation + instruction_sentence, action, closing]
        extension = (
            f"以{request.topic}为例，个体经验能够提出问题，但仍需通过系统资料来检验。"
            "当条件改变时，原有解释也可能需要调整，这正是理性探究的价值所在。"
        )
        return [opening + keyword_sentence, observation + instruction_sentence, extension, action, closing]

    @staticmethod
    def _keyword_sentence(request: GenerationRequest) -> str:
        if not request.keywords:
            return ""
        joined = "、".join(request.keywords[:6])
        return f"阅读时可以留意这些关键词：{joined}。"

    @staticmethod
    def _instruction_sentence(request: GenerationRequest) -> str:
        if not request.instruction.strip():
            return ""
        return f"本次阅读任务是：{request.instruction.strip()}。"
```

## src/llmctg/generators/transformers_backend.py

```python
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
```

## src/llmctg/io_utils.py

```python
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Iterator


class DataFormatError(ValueError):
    """输入记录无法解析时抛出。"""


def read_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"输入文件不存在: {source}")
    with source.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise DataFormatError(f"{source} 第 {line_number} 行不是有效 JSON: {error.msg}") from error
            if not isinstance(value, dict):
                raise DataFormatError(f"{source} 第 {line_number} 行必须是 JSON 对象")
            value["_line_number"] = line_number
            yield value


def append_jsonl(path: str | Path, value: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
    return target


def write_json(path: str | Path, value: Any) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return target


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return target


def existing_ids(path: str | Path, key: str = "request_id") -> set[str]:
    target = Path(path)
    if not target.exists():
        return set()
    found: set[str] = set()
    try:
        for record in read_jsonl(target):
            value = record.get(key)
            if value:
                found.add(str(value))
    except DataFormatError:
        return found
    return found
```

## src/llmctg/logging_utils.py

```python
from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(level: str = "INFO", log_file: str | Path | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        target = Path(log_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(target, encoding="utf-8"))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )
```

## src/llmctg/models.py

```python
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
```

## src/llmctg/pipeline.py

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import AppConfig
from .evaluator import ReadabilityEvaluator
from .generators import TextGenerator, create_generator
from .io_utils import append_jsonl, existing_ids, read_jsonl, write_json
from .models import GeneratedArticle, GenerationRequest, ReadingLevel
from .reporting import BatchSummary, build_summary, write_html_report, write_summary_csv
from .text_utils import stable_id

LOGGER = logging.getLogger(__name__)


class LLMCTGApplication:
    def __init__(self, config: AppConfig | None = None, generator: TextGenerator | None = None):
        self.config = config or AppConfig()
        self.generator = generator or create_generator(self.config.generation)
        self.evaluator = ReadabilityEvaluator(self.config.evaluation)

    def generate(self, request: GenerationRequest) -> list[GeneratedArticle]:
        request.validate()
        raw_results = self.generator.generate(request)
        created_at = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        articles: list[GeneratedArticle] = []
        for index, (title, content) in enumerate(raw_results):
            identifier = stable_id(request.topic, request.level.value, request.seed, index, content)
            evaluation = self.evaluator.evaluate(content, request.level)
            articles.append(
                GeneratedArticle(
                    request_id=identifier,
                    topic=request.topic,
                    level=request.level,
                    title=title,
                    content=content,
                    backend=self.generator.name,
                    created_at=created_at,
                    evaluation=evaluation,
                )
            )
        return articles

    def evaluate(self, text: str, level: ReadingLevel | str | int):
        return self.evaluator.evaluate(text, level)

    def batch(self, input_path: str | Path, output_dir: str | Path, resume: bool = True) -> BatchSummary:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        records_path = output / "articles.jsonl"
        errors_path = output / "errors.jsonl"
        done = existing_ids(records_path) if resume else set()
        articles: list[GeneratedArticle] = []
        skipped = 0
        failed = 0
        for record in read_jsonl(input_path):
            source_id = stable_id(record.get("topic", ""), record.get("level", "junior"), record.get("_line_number"))
            if source_id in done:
                skipped += 1
                continue
            try:
                request = self._request_from_record(record)
                generated = self.generate(request)
                for article in generated:
                    payload = article.to_dict()
                    payload["source_id"] = source_id
                    append_jsonl(records_path, payload)
                    articles.append(article)
                done.add(source_id)
            except Exception as error:  # 单条失败不终止批处理
                failed += 1
                LOGGER.exception("第 %s 行处理失败", record.get("_line_number"))
                append_jsonl(errors_path, {
                    "source_id": source_id,
                    "line_number": record.get("_line_number"),
                    "error_type": type(error).__name__,
                    "message": str(error),
                    "record": {key: value for key, value in record.items() if not key.startswith("_")},
                })
        summary = build_summary(articles, skipped=skipped, failed=failed)
        write_json(output / "summary.json", summary.to_dict())
        write_summary_csv(output / "summary.csv", articles)
        write_html_report(output / "report.html", articles, summary)
        return summary

    @staticmethod
    def _request_from_record(record: dict[str, Any]) -> GenerationRequest:
        keywords = record.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [item.strip() for item in keywords.replace("，", ",").split(",") if item.strip()]
        return GenerationRequest(
            topic=str(record.get("topic", "")),
            level=ReadingLevel.parse(record.get("level", "junior")),
            instruction=str(record.get("instruction", "")),
            keywords=list(keywords),
            count=int(record.get("count", 1)),
            seed=int(record["seed"]) if record.get("seed") is not None else None,
        )

    def close(self) -> None:
        self.generator.close()

    def __enter__(self) -> "LLMCTGApplication":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
```

## src/llmctg/reporting.py

```python
from __future__ import annotations

import html
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from .io_utils import write_csv
from .models import GeneratedArticle, ReadingLevel
from .text_utils import write_text


@dataclass(slots=True)
class BatchSummary:
    generated: int
    passed: int
    failed_quality: int
    skipped: int
    processing_errors: int
    average_score: float
    primary_count: int
    junior_count: int
    senior_count: int

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


def build_summary(
    articles: list[GeneratedArticle], skipped: int = 0, failed: int = 0
) -> BatchSummary:
    scores = [article.evaluation.metrics.overall_score for article in articles if article.evaluation]
    passed = sum(1 for article in articles if article.evaluation and article.evaluation.passed)
    return BatchSummary(
        generated=len(articles),
        passed=passed,
        failed_quality=len(articles) - passed,
        skipped=skipped,
        processing_errors=failed,
        average_score=round(mean(scores), 2) if scores else 0.0,
        primary_count=sum(article.level == ReadingLevel.PRIMARY for article in articles),
        junior_count=sum(article.level == ReadingLevel.JUNIOR for article in articles),
        senior_count=sum(article.level == ReadingLevel.SENIOR for article in articles),
    )


def write_summary_csv(path: str | Path, articles: list[GeneratedArticle]) -> Path:
    rows = []
    for article in articles:
        evaluation = article.evaluation
        rows.append({
            "request_id": article.request_id,
            "topic": article.topic,
            "level": article.level.value,
            "title": article.title,
            "backend": article.backend,
            "quality_grade": evaluation.quality_grade if evaluation else "",
            "passed": evaluation.passed if evaluation else False,
            "overall_score": evaluation.metrics.overall_score if evaluation else "",
            "characters": evaluation.statistics.chinese_characters if evaluation else "",
            "predicted_level": evaluation.predicted_level.value if evaluation else "",
        })
    return write_csv(path, rows, [
        "request_id", "topic", "level", "title", "backend", "quality_grade",
        "passed", "overall_score", "characters", "predicted_level",
    ])


def write_html_report(
    path: str | Path, articles: list[GeneratedArticle], summary: BatchSummary
) -> Path:
    cards = "\n".join(_article_card(article) for article in articles)
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>中文分级阅读内容质量报告</title>
<style>
body{{font-family:"Microsoft YaHei",sans-serif;margin:0;background:#f4f6f8;color:#1f2937}}
main{{max-width:1080px;margin:0 auto;padding:32px 20px}}
h1{{font-size:28px;margin:0 0 8px}} .sub{{color:#64748b;margin-bottom:24px}}
.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 28px}}
.metric,.card{{background:#fff;border:1px solid #e2e8f0;border-radius:10px;padding:16px}}
.metric strong{{display:block;font-size:25px;color:#0f4c81}} .card{{margin:14px 0}}
.meta{{color:#64748b;font-size:14px}} .content{{white-space:pre-wrap;line-height:1.85}}
.pass{{color:#177245}} .fail{{color:#b42318}} ul{{line-height:1.7}}
</style>
</head>
<body><main>
<h1>中文分级阅读内容质量报告</h1><div class="sub">批量生成与自动评估结果</div>
<section class="summary">
<div class="metric"><strong>{summary.generated}</strong>生成数量</div>
<div class="metric"><strong>{summary.passed}</strong>质量通过</div>
<div class="metric"><strong>{summary.average_score}</strong>平均得分</div>
<div class="metric"><strong>{summary.processing_errors}</strong>处理异常</div>
</section>{cards or '<p>本次没有新增文章。</p>'}
</main></body></html>"""
    return write_text(path, document)


def _article_card(article: GeneratedArticle) -> str:
    evaluation = article.evaluation
    if evaluation is None:
        return ""
    status_class = "pass" if evaluation.passed else "fail"
    status = "通过" if evaluation.passed else "待改进"
    warnings = "".join(f"<li>{html.escape(item)}</li>" for item in evaluation.warnings)
    return f"""<article class="card">
<h2>{html.escape(article.title)}</h2>
<div class="meta">{html.escape(article.level.chinese_name)} · {html.escape(article.backend)} ·
<span class="{status_class}">{status} {evaluation.metrics.overall_score} 分</span></div>
<p class="content">{html.escape(article.content)}</p>
<p><b>预测等级：</b>{html.escape(evaluation.predicted_level.chinese_name)}；
<b>汉字数：</b>{evaluation.statistics.chinese_characters}；
<b>平均句长：</b>{evaluation.statistics.average_sentence_length:.1f}</p>
{('<p><b>检查提示</b></p><ul>' + warnings + '</ul>') if warnings else ''}
</article>"""
```

## src/llmctg/text_utils.py

```python
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
```

## src/llmctg/training.py

```python
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
```

## tests/test_evaluator.py

```python
from llmctg.evaluator import ReadabilityEvaluator
from llmctg.models import ReadingLevel


def test_empty_text_fails():
    result = ReadabilityEvaluator().evaluate("", ReadingLevel.PRIMARY)
    assert not result.passed
    assert "文本为空" in result.warnings


def test_evaluation_has_statistics():
    text = "春天来了。小草从泥土里探出头。我们走到公园，发现树枝上长出了新叶。\n大家把看到的变化写进观察本。"
    result = ReadabilityEvaluator().evaluate(text, ReadingLevel.PRIMARY)
    assert result.statistics.sentences == 4
    assert result.statistics.paragraphs == 2
    assert 0 <= result.metrics.overall_score <= 100


def test_repetition_warning():
    text = "春风吹来了，春风吹来了，春风吹来了，春风吹来了。\n我们听见春风吹来了。"
    result = ReadabilityEvaluator().evaluate(text, ReadingLevel.PRIMARY)
    assert result.metrics.repetition_rate > 0
    assert any("重复" in item for item in result.warnings)
```

## tests/test_lora_generation.py

```python
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
```

## tests/test_models.py

```python
import pytest

from llmctg.models import GenerationRequest, ReadingLevel


def test_reading_level_aliases():
    assert ReadingLevel.parse("小学") is ReadingLevel.PRIMARY
    assert ReadingLevel.parse("1") is ReadingLevel.JUNIOR
    assert ReadingLevel.parse("SENIOR") is ReadingLevel.SENIOR


def test_invalid_reading_level():
    with pytest.raises(ValueError):
        ReadingLevel.parse("大学")


def test_request_validation():
    request = GenerationRequest(topic="  海洋  ", level="初中", keywords=[" 生物 ", ""])
    request.validate()
    assert request.topic == "海洋"
    assert request.level is ReadingLevel.JUNIOR
    assert request.keywords == ["生物"]


@pytest.mark.parametrize("count", [0, 21])
def test_request_count_range(count):
    with pytest.raises(ValueError):
        GenerationRequest(topic="测试", count=count).validate()
```

## tests/test_pipeline.py

```python
import json

from llmctg.config import AppConfig
from llmctg.models import GenerationRequest, ReadingLevel
from llmctg.pipeline import LLMCTGApplication


def test_generate_offline_article():
    with LLMCTGApplication(AppConfig()) as studio:
        articles = studio.generate(GenerationRequest(topic="月亮", level=ReadingLevel.PRIMARY, seed=7))
    assert len(articles) == 1
    assert articles[0].topic == "月亮"
    assert articles[0].evaluation is not None


def test_batch_continues_after_bad_record(tmp_path):
    source = tmp_path / "tasks.jsonl"
    source.write_text(
        "\n".join([
            json.dumps({"topic": "河流", "level": "junior"}, ensure_ascii=False),
            json.dumps({"topic": "", "level": "junior"}, ensure_ascii=False),
        ]),
        encoding="utf-8",
    )
    with LLMCTGApplication(AppConfig()) as studio:
        summary = studio.batch(source, tmp_path / "output")
    assert summary.generated == 1
    assert summary.processing_errors == 1
    assert (tmp_path / "output" / "report.html").exists()
```

## tests/test_text_utils.py

```python
from llmctg.text_utils import (
    ensure_terminal_punctuation,
    normalize_text,
    repetition_rate,
    safe_filename,
    split_sentences,
    stable_id,
)


def test_normalize_text():
    assert normalize_text("  春天   来了\r\n\r\n 小草发芽 ") == "春天 来了\n小草发芽"


def test_sentence_helpers():
    text = ensure_terminal_punctuation("春天来了。小草发芽")
    assert text.endswith("。")
    assert len(split_sentences(text)) == 2


def test_repetition_rate_detects_duplicate_ngram():
    assert repetition_rate("春风吹春风吹春风吹", size=3) > 0
    assert repetition_rate("春夏秋冬", size=4) == 0


def test_stable_id_is_deterministic():
    assert stable_id("a", 1) == stable_id("a", 1)
    assert stable_id("a", 1) != stable_id("a", 2)


def test_safe_filename():
    assert safe_filename('报告:"测试"/一') == "报告__测试__一"
```
