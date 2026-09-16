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
