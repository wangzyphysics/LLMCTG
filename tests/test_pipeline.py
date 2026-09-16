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
