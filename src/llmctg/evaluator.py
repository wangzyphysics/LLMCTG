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
