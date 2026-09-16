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
