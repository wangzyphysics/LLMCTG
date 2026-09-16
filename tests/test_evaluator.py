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
