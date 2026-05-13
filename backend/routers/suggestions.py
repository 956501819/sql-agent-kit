import os
import yaml
from fastapi import APIRouter
from backend.services.agent_service import CONFIG_DIR, DATA_DIR, ENV_PATH

router = APIRouter()


def _load_schema_context() -> str:
    """读取表白名单和 schema 注释，拼成 LLM 可用的上下文"""
    parts = []

    tables_path = os.path.join(DATA_DIR, "tables.yaml")
    if os.path.exists(tables_path):
        with open(tables_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        tables = data.get("allowed_tables", [])
        if tables:
            parts.append("可用数据表：" + "、".join(tables))

    annotations_path = os.path.join(DATA_DIR, "schema_annotations.yaml")
    if os.path.exists(annotations_path):
        with open(annotations_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            parts.append("字段业务含义：\n" + content)

    return "\n\n".join(parts)


@router.get("/suggestions")
async def get_suggestions():
    """根据 schema 让 LLM 生成数据分析建议"""
    import asyncio

    schema_context = _load_schema_context()
    if not schema_context:
        return {"suggestions": []}

    system_prompt = """你是一位数据分析专家。根据用户提供的数据库结构，生成 6 条有价值的数据分析问题建议。

要求：
1. 每条建议是一个完整的自然语言问题，用户可以直接拿去查询
2. 优先生成能产出图表的分析问题，每个建议应明确包含：
   - 时间维度（按月/按周/按天看趋势）→ 折线图/面积图
   - 或多指标对比（量和率同时看，如"销售额及增长率"）→ 双轴图
   - 或分类排名（TOP N、按品类/渠道对比）→ 柱状图/饼图
3. 避免生成只会返回明细列表的问题（如"列出所有X"、"查看某条记录"）
4. 问题要具体，包含时间范围或具体指标
5. 只输出 JSON 数组，不要任何解释

输出格式：
["建议1", "建议2", "建议3", "建议4", "建议5", "建议6"]"""

    user_content = f"数据库结构如下：\n\n{schema_context}\n\n请生成 6 条分析建议。"

    def _do_llm():
        from sql_agent.llm import get_llm_client
        from sql_agent._config import load_settings
        settings = load_settings(config_dir=CONFIG_DIR, env_file=ENV_PATH)
        llm = get_llm_client(settings["llm"])
        return llm.chat(
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": user_content}],
            temperature=0.7,
        )

    try:
        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(None, _do_llm)

        import re, json
        match = re.search(r"\[[\s\S]+\]", raw)
        suggestions = json.loads(match.group()) if match else []
        return {"suggestions": suggestions[:6]}

    except Exception as e:
        return {"suggestions": [], "error": str(e)}
