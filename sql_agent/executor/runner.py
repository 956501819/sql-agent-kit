from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import re


class SQLRunner:
    """
    SQL 执行器
    核心特性：执行失败时把错误信息回传给 LLM，让模型自我修正（最多 N 次）
    这是 Agent 系统"错误自愈"能力的核心实现
    """

    def __init__(self, engine: Engine, timeout: int = 30, max_rows: int = 500):
        self._engine = engine
        self._timeout = timeout
        self._max_rows = max_rows

    def run(self, sql: str) -> tuple[bool, list[dict] | str]:
        """
        执行 SQL 并返回结果
        :return: (success, data_or_error_message)
                 success=True  → data 是 list[dict]（行数据）
                 success=False → data 是 str（错误信息，用于反馈给 LLM 重试）
        """
        # 确保有 LIMIT，保护查询
        sql = self._ensure_limit(sql)

        try:
            with self._engine.connect() as conn:
                # 设置超时（MySQL/PostgreSQL 均支持）
                if "mysql" in str(self._engine.url):
                    conn.execute(text(f"SET SESSION max_execution_time={self._timeout * 1000}"))
                elif "postgresql" in str(self._engine.url):
                    conn.execute(text(f"SET statement_timeout = '{self._timeout}s'"))

                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = [dict(zip(columns, row)) for row in result.fetchall()]
                return True, rows

        except SQLAlchemyError as e:
            # 提取核心错误信息，去掉 SQLAlchemy 的内部堆栈
            error_msg = self._extract_db_error(str(e))
            return False, error_msg

        except Exception as e:
            return False, f"执行异常: {str(e)}"

    def _ensure_limit(self, sql: str) -> str:
        """如果 SQL 没有 LIMIT，自动追加，防止返回超大结果集"""
        sql_upper = sql.upper()
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip().rstrip(";")
            sql += f" LIMIT {self._max_rows}"
        return sql

    def _extract_db_error(self, error_str: str) -> str:
        """提取数据库错误的核心信息，去掉 Python 堆栈"""
        # 提取括号内的数据库原始错误
        match = re.search(r"\(.*?\)\s*(.*)", error_str, re.DOTALL)
        if match:
            return match.group(1).strip()[:500]  # 限制长度
        return error_str[:500]
