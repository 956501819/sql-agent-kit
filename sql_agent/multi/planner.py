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
  "chart_hint": {
    "type": "图表类型（见下方规则）",
    "x": "X 轴列名（用 SQL 查询中预期的列名，不确定时留空字符串）",
    "y": "主 Y 轴列名（最关键的指标列名，不确定时留空字符串）",
    "y2": "副 Y 轴列名（仅当需要双 Y 轴时填写，如同时展示销售额和增长率；否则留空字符串）",
    "sort": "排序方式：desc=按 Y 轴降序、asc=按 Y 轴升序、none=不排序（时间序列用 none）",
    "label": true 或 false（是否在图表上显示数据标签）
  },
  "sub_questions": ["..."]
}

chart_hint.type 选择规则：
- 单指标随时间变化的趋势 → line
- 多分类随时间变化的趋势（面积堆叠更直观） → area
- 分类对比/排名（分组展示） → bar
- 多指标构成对比/堆叠 → bar_stack
- 占比/构成分析（类别不超过8个） → pie
- 两个数值指标的相关性 → scatter
- 转化率/流程各环节数量递减 → funnel
- 两个维度交叉的数值分布（如星期×小时） → heatmap
- 量与率同时展示（如销售额+增长率） → dual_axis
- 明细列表/无明确图表需求 → table

sort 建议：
- 排名/对比类问题（最高/最低/TOP N）→ desc
- 时间趋势类问题 → none
- 其他 → none

label 建议：
- 数据点较少（≤ 15 行）→ true
- 数据点较多（> 15 行）→ false

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
        chart_hint = plan.get("chart_hint", {"type": "table", "x": "", "y": "", "y2": "", "sort": "none", "label": False})
        # 兼容旧格式：LLM 仍返回字符串时包装成 dict
        if isinstance(chart_hint, str):
            chart_hint = {"type": chart_hint, "x": "", "y": "", "y2": "", "sort": "none", "label": False}
        sub_questions = plan.get("sub_questions", [question])

        chart_type = chart_hint.get("type", "table")
        log.append(
            f"   ✅ 意图：{intent}\n"
            f"   📊 建议图表：{chart_type}  x={chart_hint.get('x') or '自动'}  y={chart_hint.get('y') or '自动'}"
            + (f"  y2={chart_hint.get('y2')}" if chart_hint.get("y2") else "")
            + f"  sort={chart_hint.get('sort', 'none')}  label={chart_hint.get('label', False)}\n"
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
            "intent": "",
            "chart_hint": {"type": "table", "x": "", "y": "", "y2": "", "sort": "none", "label": False},
            "sub_questions": [question],
            "error": f"Planner 降级（{e}），使用原始问题继续",
            "process_log": log,
        }
