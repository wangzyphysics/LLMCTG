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
