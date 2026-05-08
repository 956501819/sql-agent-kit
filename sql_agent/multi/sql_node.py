"""
SQL Agent 节点 — 复用现有 SQLAgent，包装为 LangGraph 节点
输入：state["sub_questions"]
输出：state["sql_results"]
"""

from .state import GraphState


def sql_node(state: GraphState) -> GraphState:
    """SQL Agent 节点：遍历子问题，逐一执行 SQL 查询"""
    from sql_agent import build_agent

    sub_questions = state.get("sub_questions", [state["question"]])
    log = list(state.get("process_log") or [])
    log.append(f"💬 [SQL Agent] 准备执行 {len(sub_questions)} 个查询...")

    try:
        agent = build_agent()
    except Exception as e:
        log.append(f"   ❌ Agent 初始化失败：{e}")
        return {
            **state,
            "sql_results": [],
            "error": f"SQL Agent 初始化失败: {e}",
            "process_log": log,
        }

    results = []
    all_failed = True

    for i, q in enumerate(sub_questions, 1):
        try:
            result = agent.query(q)
            result_dict = {
                "question": result.question,
                "sql": result.sql,
                "success": result.success,
                "data": result.data,
                "formatted_table": result.formatted_table,
                "error": result.error,
                "confidence": result.confidence,
                "retry_count": result.retry_count,
                "need_confirm": result.need_confirm,
            }
            results.append(result_dict)
            if result.success:
                all_failed = False
                retry_info = f"，重试 {result.retry_count} 次" if result.retry_count > 0 else ""
                log.append(
                    f"   ✅ 子问题 {i}：{q}\n"
                    f"   SQL：{result.sql.strip()}\n"
                    f"   置信度：{result.confidence:.0%}，返回 {len(result.data)} 行{retry_info}"
                )
            else:
                log.append(
                    f"   ❌ 子问题 {i}：{q}\n"
                    f"   SQL：{result.sql.strip() or '（未生成）'}\n"
                    f"   错误：{result.error}"
                )
        except Exception as e:
            results.append({
                "question": q,
                "sql": "",
                "success": False,
                "data": [],
                "formatted_table": "",
                "error": str(e),
                "confidence": 0.0,
                "retry_count": 0,
                "need_confirm": False,
            })
            log.append(f"   ❌ 子问题 {i} 异常：{e}")

    error = state.get("error")
    if all_failed and results:
        error = results[-1].get("error", "所有查询均失败")

    return {
        **state,
        "sql_results": results,
        "error": error,
        "process_log": log,
    }
