from .store import FewShotStore


class FewShotRetriever:
    """
    Few-shot 示例检索器
    根据当前问题，从示例库中找出最相似的 K 个示例注入 Prompt
    使用关键词重叠做轻量级相似度计算（无需额外模型，部署简单）
    """

    def __init__(self, store: FewShotStore, top_k: int = 3):
        self._store = store
        self._top_k = top_k

    def retrieve(self, question: str) -> list[dict]:
        """
        检索最相似的示例
        :return: [{"question": ..., "sql": ...}, ...]
        """
        examples = self._store.list_all()
        if not examples:
            return []

        if len(examples) <= self._top_k:
            return examples

        # 关键词重叠评分（Jaccard 相似度的简化版）
        q_words = set(question.lower().split())
        scored = []
        for ex in examples:
            ex_words = set(ex["question"].lower().split())
            if not q_words or not ex_words:
                score = 0.0
            else:
                intersection = q_words & ex_words
                union = q_words | ex_words
                score = len(intersection) / len(union)
            scored.append((score, ex))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [ex for _, ex in scored[: self._top_k]]

    def format_for_prompt(self, examples: list[dict]) -> str:
        """格式化示例为 Prompt 文本"""
        if not examples:
            return ""
        lines = ["### 参考示例（历史上类似问题的正确SQL）\n"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"示例{i}:")
            lines.append(f"  问题: {ex['question']}")
            lines.append(f"  SQL: {ex['sql']}\n")
        return "\n".join(lines)
