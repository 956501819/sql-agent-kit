import json
import os
import fcntl
from datetime import datetime
from pathlib import Path


class QueryLogger:
    """
    查询日志记录器
    以 JSONL 格式记录每次查询，用于：
    1. 分析高频失败场景
    2. 收集错误案例 → 自动补充到 Few-shot 库
    3. 面试时展示系统的可观测性设计
    """

    def __init__(self, log_path: str = "./logs/queries.jsonl"):
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        question: str,
        sql: str,
        success: bool,
        rows_count: int = 0,
        error: str = "",
        retry_count: int = 0,
        confidence: float = 1.0,
        judge_scores: dict = None,
        summary: str = "",
        chart_json: str = "",
    ):
        record = {
            "ts": datetime.now().isoformat(),
            "question": question,
            "sql": sql,
            "success": success,
            "rows_count": rows_count,
            "error": error,
            "retry_count": retry_count,
            "confidence": confidence,
        }
        if judge_scores:
            record["judge_scores"] = judge_scores
        if summary:
            record["summary"] = summary
        if chart_json:
            record["chart_json"] = chart_json
        with open(self._path, "a", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
