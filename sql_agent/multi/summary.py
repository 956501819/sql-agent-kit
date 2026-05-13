"""
Summary Agent — 根据查询结果生成自然语言分析结论
"""

from .state import GraphState


_SYSTEM_PROMPT = """你是一位数据分析师，擅长用简洁的语言解读数据。
根据用户问题、查询到的数据，输出 2-4 句的分析结论。
要求：
1. 直接说明关键数字和趋势
2. 指出最重要的发现或异常
3. 语言简洁、中文输出
4. 不要重复用户的问题，直接给出结论
"""


def summary_node(state: GraphState) -> GraphState:
    """Summary Agent 节点：生成自然语言分析结论"""
    from sql_agent.llm import get_llm_client
    from sql_agent._config import load_settings

    question = state.get("question", "")
    intent = state.get("intent", question)
    sql_results = state.get("sql_results", [])
    log = list(state.get("process_log") or [])
    log.append("📝 [Summary Agent] 正在生成分析结论...")

    data_summary_parts = []
    for r in sql_results:
        if r.get("success") and r.get("data"):
            sub_q = r.get("question", "")
            rows = r["data"][:5]
            total = len(r["data"])
            rows_text = "\n".join(str(row) for row in rows)
            snippet = f"子问题：{sub_q}\n共 {total} 行数据（展示前5行）：\n{rows_text}"
            data_summary_parts.append(snippet)

    if not data_summary_parts:
        log.append("   ⚠️ 无有效数据，返回默认提示")
        return {
            **state,
            "summary": "未能获取有效数据，无法生成分析结论。",
            "process_log": log,
        }

    data_summary = "\n\n".join(data_summary_parts)

    user_content = (
        f"用户问题：{question}\n"
        f"分析意图：{intent}\n\n"
        f"查询结果：\n{data_summary}"
    )

    try:
        settings = load_settings()
        llm = get_llm_client(settings["llm"])

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        summary = llm.chat(messages, temperature=0.3)
        log.append(f"   ✅ 结论已生成（{len(summary.strip())} 字）")
        return {**state, "summary": summary.strip(), "process_log": log}

    except Exception as e:
        log.append(f"   ❌ 结论生成失败：{e}")
        return {
            **state,
            "summary": f"结论生成失败（{e}），请查看上方数据表格。",
            "process_log": log,
        }
