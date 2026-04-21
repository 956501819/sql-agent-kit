class SchemaSelector:
    """
    智能表筛选器：根据用户问题，从白名单表中筛选出相关的表
    解决的问题：数据库表多时，把全部 Schema 注入 Prompt 会超出 Context 限制
    策略：关键词匹配 + 表名/描述相似度，先粗筛，再精排
    """

    def __init__(self, max_tables: int = 10):
        self._max_tables = max_tables

    def select(
        self,
        question: str,
        enriched_schema: dict[str, dict],
    ) -> dict[str, dict]:
        """
        根据问题筛选最相关的表
        :param question: 用户的自然语言问题
        :param enriched_schema: 已注入语义注释的完整 schema
        :return: 筛选后的子集 schema
        """
        # 表数量在限制内，直接全部返回
        if len(enriched_schema) <= self._max_tables:
            return enriched_schema

        # 关键词匹配打分
        question_lower = question.lower()
        scored = []

        for table_name, info in enriched_schema.items():
            score = 0

            # 表名直接出现在问题中 → 高分
            if table_name.lower() in question_lower:
                score += 10

            # 表描述中的关键词出现在问题中
            desc = info.get("description", "").lower()
            for word in question_lower.split():
                if len(word) > 1 and word in desc:
                    score += 2

            # 字段名出现在问题中
            for col in info.get("columns", []):
                col_name = col["name"].lower()
                if col_name in question_lower:
                    score += 3
                col_desc = col.get("description", "").lower()
                for word in question_lower.split():
                    if len(word) > 1 and word in col_desc:
                        score += 1

            scored.append((table_name, score))

        # 按分数降序，取 top N
        scored.sort(key=lambda x: x[1], reverse=True)
        selected_tables = [t for t, _ in scored[: self._max_tables]]

        return {t: enriched_schema[t] for t in selected_tables}
