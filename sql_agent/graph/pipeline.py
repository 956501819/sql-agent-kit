"""
LangGraph Pipeline — 多 Agent 编排
构建 Planner → SQL → Chart → Summary → Judge 的有向图
"""

from langgraph.graph import StateGraph, END

from sql_agent.agents.state import GraphState
from sql_agent.agents.planner import planner_node
from sql_agent.agents.sql_node import sql_node
from sql_agent.agents.chart import chart_node
from sql_agent.agents.summary import summary_node
from sql_agent.agents.judge import judge_node


def _route_after_sql(state: GraphState) -> str:
    """SQL Agent 后的路由：所有查询均失败时直接结束，否则继续"""
    sql_results = state.get("sql_results", [])
    any_success = any(r.get("success") for r in sql_results)
    return "ok" if any_success else "error"


def build_pipeline():
    """
    构建并编译 LangGraph 多 Agent Pipeline

    图结构：
        planner → sql_agent
                       ↓ (ok)    → chart_agent → summary_agent → judge_agent → END
                       ↓ (error) → END
    """
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("sql_agent", sql_node)
    graph.add_node("chart_agent", chart_node)
    graph.add_node("summary_agent", summary_node)
    graph.add_node("judge_agent", judge_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "sql_agent")
    graph.add_conditional_edges(
        "sql_agent",
        _route_after_sql,
        {"ok": "chart_agent", "error": END},
    )
    graph.add_edge("chart_agent", "summary_agent")
    graph.add_edge("summary_agent", "judge_agent")
    graph.add_edge("judge_agent", END)

    return graph.compile()
