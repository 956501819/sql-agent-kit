"""
Planner Agent — 意图拆解节点
输入：用户原始问题
输出：intent / chart_hint / sub_questions
"""

import json
import re
from .state import GraphState


_SYSTEM_PROMPT = """你是一个数据分析意图理解专家。
根据用户的问题，输出 JSON 格式的分析计划，不要任何解释，只输出 JSON。

输出格式：
{
  "intent": "一句话描述用户想了解什么",
  "chart_hint": "bar 或 line 或 pie 或 scatter 或 table",
  "sub_questions": ["..."]
}

chart_hint 选择规则：
- 时间趋势/走势 → line
- 分类对比/排名 → bar
- 占比/构成 → pie
- 两个数值的相关性 → scatter
- 明细列表/无明确趋势 → table

sub_questions：大多数问题输出单元素列表即可，只有当问题明显包含多个独立子问题时才拆分。
"""


def planner_node(state: GraphState) -> GraphState:
    """Planner 节点：分析意图，返回 intent / chart_hint / sub_questions"""
    from sql_agent.llm import get_llm_client
    from sql_agent._config import load_settings

    question = state["question"]
    log = list(state.get("process_log") or [])
    log.append("🔍 [Planner Agent] 正在分析问题意图...")

    try:
        settings = load_settings()
        llm = get_llm_client(settings["llm"])

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题：{question}"},
        ]
        raw = llm.chat(messages, temperature=0.0)

        # 提取 JSON（兼容 LLM 返回 ```json ... ``` 包裹）
        match = re.search(r"\{[\s\S]+\}", raw)
        if not match:
            raise ValueError(f"Planner LLM 未返回有效 JSON: {raw[:200]}")
        plan = json.loads(match.group())

        intent = plan.get("intent", question)
        chart_hint = plan.get("chart_hint", "table")
        sub_questions = plan.get("sub_questions", [question])

        log.append(
            f"   ✅ 意图：{intent}\n"
            f"   📊 建议图表：{chart_hint}\n"
            f"   📋 子问题（{len(sub_questions)} 个）：{' | '.join(sub_questions)}"
        )

        return {
            **state,
            "intent": intent,
            "chart_hint": chart_hint,
            "sub_questions": sub_questions,
            "process_log": log,
        }

    except Exception as e:
        log.append(f"   ⚠️ Planner 降级（{e}），直接使用原始问题")
        return {
            **state,
            "intent": question,
            "chart_hint": "table",
            "sub_questions": [question],
            "error": f"Planner 降级（{e}），使用原始问题继续",
            "process_log": log,
        }
