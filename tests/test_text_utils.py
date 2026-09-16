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
