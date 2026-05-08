"""
GraphState — LangGraph 共享状态定义
所有 Agent 节点读写同一个 state dict
"""

from typing import TypedDict, Optional, List


class GraphState(TypedDict, total=False):
    # 用户输入
    question: str

    # Planner 输出
    intent: str           # 意图摘要，如"分析上月销售趋势"
    chart_hint: dict       # 结构化图表指令：{type, x, y, y2, sort, label}
    sub_questions: List[str]   # 拆解后的子问题列表（单问题时 = [question]）

    # SQL Agent 输出
    sql_results: List[dict]   # 每项对应一个 QueryResult 序列化后的 dict
    # 每个 dict 字段: question/sql/success/data/formatted_table/error/confidence/retry_count

    # Chart Agent 输出
    chart_json: str       # plotly figure.to_json()，空字符串表示无图表
    chart_source_index: int  # 画图所用的 sql_results 索引，与页面展示保持一致

    # Summary Agent 输出
    summary: str          # 2-4 句自然语言分析结论

    # Judge 输出
    judge_scores: dict    # {sql_correctness:0-10, chart_fitness:0-10, summary_quality:0-10}

    # 错误处理
    error: Optional[str]

    # 思考过程日志（每个 Agent 节点追加一条）
    process_log: List[str]
