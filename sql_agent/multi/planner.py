"""
Planner Agent — 意图拆解节点
输入：用户原始问题
输出：intent / sub_questions
"""

import json
import re
from .state import GraphState


_SYSTEM_PROMPT = """你是一个数据分析意图理解专家。
根据用户的问题，输出 JSON 格式的分析计划，不要任何解释，只输出 JSON。

输出格式：
{
  "intent": "一句话描述用户想了解什么",
  "sub_questions": ["..."]
}

sub_questions 拆分原则：
- 如果多个指标属于同一个数据源、同一个时间范围、同一个分组维度，只输出一个合并的子问题
  例如"每月销售额和订单量趋势" → ["每月销售额和订单量变化趋势"]
  而不是拆成 ["每月销售额趋势", "每月订单量趋势"]
- 只有当问题包含明显不相关的独立议题时才拆分（如"分析用户增长趋势，同时评估库存周转率"）
- 大多数情况输出单元素列表即可
"""


def planner_node(state: GraphState) -> GraphState:
    """Planner 节点：分析意图，返回 intent / sub_questions"""
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
        sub_questions = plan.get("sub_questions", [question])

        log.append(
            f"   ✅ 意图：{intent}\n"
            f"   📋 子问题（{len(sub_questions)} 个）：{' | '.join(sub_questions)}"
        )

        return {
            **state,
            "intent": intent,
            "sub_questions": sub_questions,
            "process_log": log,
        }

    except Exception as e:
        log.append(f"   ⚠️ Planner 降级（{e}），直接使用原始问题")
        return {
            **state,
            "intent": "",
            "sub_questions": [question],
            "error": f"Planner 降级（{e}），使用原始问题继续",
            "process_log": log,
        }
