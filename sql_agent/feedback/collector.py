import json
from pathlib import Path
from datetime import datetime


class FeedbackCollector:
    """
    用户反馈收集器
    用户可以对查询结果标记"正确"或"错误"
    错误案例自动归档，可手动修正后加入 Few-shot 库
    """

    def __init__(self, log_path: str = "./logs/queries.jsonl"):
        self._log_path = Path(log_path)

    def mark_correct(self, question: str, sql: str):
        """标记一个问题-SQL 对为正确，可用于加入 Few-shot"""
        self._append_feedback(question, sql, feedback="correct")

    def mark_wrong(self, question: str, sql: str, comment: str = ""):
        """标记为错误，记录供后续分析"""
        self._append_feedback(question, sql, feedback="wrong", comment=comment)

    def _append_feedback(self, question: str, sql: str, feedback: str, comment: str = ""):
        record = {
            "ts": datetime.now().isoformat(),
            "type": "feedback",
            "question": question,
            "sql": sql,
            "feedback": feedback,
            "comment": comment,
        }
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
