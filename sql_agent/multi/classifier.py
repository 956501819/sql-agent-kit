"""
前置分类器 — 规则型简单问题判断
在 Planner 之前执行，命中简单模式时直接跳过 Planner 进入 SQL Agent
"""

import re
from .state import GraphState

# 分析类关键词：包含这些词的问题需要 Planner 拆解意图
_ANALYTICAL_KEYWORDS = [
    "趋势", "对比", "比较", "分析", "同比", "环比",
    "预测", "推荐", "排名", "TOP", "top",
    "最高", "最低", "最大", "最小", "最多", "最少",
    "增长", "下降", "变化", "波动", "异常",
    "占比", "比例", "分布", "汇总", "统计",
    "转化", "漏斗", "留存", "复购",
]

# 简单查询模式：匹配"查/看/列出 + 表名"的请求
_SIMPLE_PATTERNS = [
    re.compile(r"(查|查看|查询|看|看看|显示|列出|获取|导出)"
               r"(一下|下)?(所有|全部|全|整个)?(的|下)?"
               r"(?P<table>[a-zA-Z_\u4e00-\u9fff]+)"
               r"(表|数据|记录|信息|列表)?(吧|吗|呢)?"),
]


def classify_query(question: str, table_names: list) -> bool:
    """
    规则判断问题是否为"简单查询"。

    简单查询定义：用户想查某张表的全量或基本数据，不涉及聚合/对比/趋势等分析。

    Returns:
        True: 简单查询，应跳过 Planner
        False: 需要 Planner 拆解意图
    """
    if not question or not question.strip():
        return False

    text = question.strip()

    # 1. 检查是否包含分析类关键词 → 非简单
    for kw in _ANALYTICAL_KEYWORDS:
        if kw in text:
            return False

    # 2. 检查是否匹配简单查询模式
    table_set = {t.lower() for t in table_names}
    for pattern in _SIMPLE_PATTERNS:
        m = pattern.search(text)
        if m:
            table_hint = m.group("table").lower()
            # 模糊匹配：检查命中的表名片段是否在已知表名中
            for t in table_set:
                if table_hint in t or t in table_hint:
                    return True
            # 表名不匹配时，不走 Planner（可能是 LLM 也不知道的模糊输入）

    # 3. 极短问题（≤5字且包含已知表名），直接跳过 Planner
    if len(text) <= 5 and any(t in text.lower() for t in table_set):
        return True

    return False


def classifier_node(state: GraphState) -> GraphState:
    """
    LangGraph 节点：判断是否跳过 Planner。

    规则：
    1. 问题包含分析关键词 → 走 Planner
    2. 问题匹配简单查询模式 → 跳过 Planner
    3. 其他 → 走 Planner（保守策略）
    """
    from sql_agent._config import load_table_names

    question = state.get("question", "")
    log = list(state.get("process_log") or [])

    try:
        table_names = load_table_names()
    except Exception:
        table_names = []

    skip = classify_query(question, table_names)

    if skip:
        log.append("⚡ [分类器] 检测到简单查询，跳过 Planner，直接生成 SQL")
        return {
            **state,
            "skip_planner": True,
            "intent": "",
            "sub_questions": [question],
            "process_log": log,
        }

    log.append("🧠 [分类器] 检测到分析类问题，进入 Planner 拆解意图")
    return {
        **state,
        "skip_planner": False,
        "process_log": log,
    }
