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
