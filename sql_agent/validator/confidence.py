import re


class ConfidenceEstimator:
    """
    置信度评估器
    根据生成的 SQL 特征评估可靠性，低于阈值时提示用户确认
    这是避免"语法正确但语义错误"静默失败的关键机制

    评分维度：
    1. SQL 结构完整性（有无核心子句）
    2. 是否涉及复杂逻辑（子查询、多重JOIN）
    3. 是否有明显的占位符或不确定表达
    """

    def estimate(self, sql: str, question: str = "") -> float:
        """
        返回 0~1 的置信度分数
        """
        score = 1.0
        sql_upper = sql.upper()

        # === 扣分项 ===

        # 包含明显的占位符
        placeholders = re.findall(
            r"\b(YOUR_TABLE|YOUR_COLUMN|PLACEHOLDER|TODO|FIXME|\?\?\?)\b",
            sql, re.IGNORECASE
        )
        if placeholders:
            score -= 0.4

        # 复杂子查询（每一层扣分）
        subquery_count = sql.count("SELECT") - 1
        if subquery_count > 0:
            score -= min(subquery_count * 0.1, 0.3)

        # 超过 3 个 JOIN（复杂关联，准确率下降）
        join_count = len(re.findall(r"\bJOIN\b", sql_upper))
        if join_count > 3:
            score -= (join_count - 3) * 0.05

        # 包含 * 通配符（可能不够精确）
        if "SELECT *" in sql_upper or "SELECT\n*" in sql_upper:
            score -= 0.05

        # 使用了可能有歧义的函数
        ambiguous_funcs = re.findall(r"\b(NOW|CURDATE|CURRENT_DATE|GETDATE)\b", sql_upper)
        if ambiguous_funcs:
            score -= 0.05  # 时间函数结果依赖执行时刻，轻微扣分

        # 没有 WHERE 子句的聚合查询（可能返回全表数据）
        if "GROUP BY" in sql_upper and "WHERE" not in sql_upper:
            score -= 0.1

        # === 加分项 ===

        # 使用了 LIMIT（说明模型有意控制数据量）
        if "LIMIT" in sql_upper:
            score += 0.05

        return max(0.0, min(1.0, round(score, 2)))
