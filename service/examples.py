"""按题型挑示例：示例库里每个题型只有一两个审核过的代码，新题判断题型后取最相关的两个交给 DeepSeek。

题型很少，示例也少，用关键词就能分得准，不需要向量数据库。
"""

import json

from . import settings

INDEX = settings.ROOT / "render" / "examples" / "index.json"
EXAMPLES_PER_PROMPT = 2


def _index():
    return json.loads(INDEX.read_text(encoding="utf-8"))


def classify(text):
    """按关键词出现的次数给题型打分，返回 [(题型, 分数)]，分数高的在前，只含分数大于 0 的。"""
    scores = []
    for category, keywords in _index()["categories"].items():
        score = sum(text.count(keyword) for keyword in keywords)
        if score:
            scores.append((category, score))
    return sorted(scores, key=lambda item: -item[1])


def pick(text):
    """挑出要给模型看的示例文件名。先按题型匹配，不够两个时用默认示例补上。"""
    index = _index()
    by_category = {}
    for example in index["examples"]:
        by_category.setdefault(example["category"], []).append(example["file"])
    chosen = []
    for category, _ in classify(text):
        for name in by_category.get(category, []):
            if name not in chosen:
                chosen.append(name)
    for name in index["default"]:
        if name not in chosen:
            chosen.append(name)
    return chosen[:EXAMPLES_PER_PROMPT]


def main_category(text):
    """这道题最可能的题型，没有匹配时返回 None。"""
    ranked = classify(text)
    return ranked[0][0] if ranked else None


def has_example(category):
    return any(example["category"] == category for example in _index()["examples"])
