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
