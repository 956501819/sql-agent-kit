import os
import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.agent_service import CONFIG_DIR, DATA_DIR, ENV_PATH
from backend.utils import sanitize

router = APIRouter()

_ANNOTATIONS_PATH = os.path.join(DATA_DIR, "schema_annotations.yaml")
_TABLES_PATH = os.path.join(DATA_DIR, "tables.yaml")


@router.get("/annotations")
async def get_annotations():
    if not os.path.exists(_ANNOTATIONS_PATH):
        return {"content": ""}
    with open(_ANNOTATIONS_PATH, "r", encoding="utf-8") as f:
        return {"content": f.read()}


class AnnotationsPayload(BaseModel):
    content: str


@router.post("/annotations")
async def save_annotations(payload: AnnotationsPayload):
    from backend.services.agent_service import reset_agent
    try:
        yaml.safe_load(payload.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML 格式错误: {e}")
    with open(_ANNOTATIONS_PATH, "w", encoding="utf-8") as f:
        f.write(payload.content)
    reset_agent()
    return {"message": "Schema 注释已保存"}


@router.post("/annotations/generate")
async def generate_annotations():
    """
    自动生成 schema 注释：
    1. 读取白名单表
    2. 用 SQLAlchemy inspector 获取表结构
    3. 每表抽取 3 条样本数据
    4. 交给 LLM 生成 YAML 格式注释
    """
    from dotenv import load_dotenv
    from sqlalchemy import create_engine, inspect, text
    from sql_agent._config import load_settings
    from sql_agent.llm import get_llm_client

    load_dotenv(ENV_PATH)

    # 读取白名单
    if not os.path.exists(_TABLES_PATH):
        raise HTTPException(status_code=400, detail="未找到 tables.yaml，请先配置表白名单")
    with open(_TABLES_PATH, "r", encoding="utf-8") as f:
        tables_data = yaml.safe_load(f) or {}
    allowed_tables = tables_data.get("allowed_tables", [])
    if not allowed_tables:
        raise HTTPException(status_code=400, detail="白名单为空，请先添加表")

    # 建立数据库连接
    db_type = os.getenv("DB_TYPE", "mysql")
    if db_type == "sqlite":
        sqlite_path = os.getenv("DB_SQLITE_PATH", "./data/local.db")
        url = f"sqlite:///{sqlite_path}"
        connect_args = {}
    elif db_type == "postgresql":
        url = (f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
               f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}")
        connect_args = {"connect_timeout": 10}
    else:
        url = (f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
               f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME')}")
        connect_args = {"connect_timeout": 10}

    try:
        engine = create_engine(url, connect_args=connect_args)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {e}")

    # 获取表结构 + 样本数据
    schema_parts = []
    try:
        inspector = inspect(engine)
        # Use dialect-appropriate quoting
        dialect = engine.dialect.name  # mysql / postgresql / sqlite
        def quote_table(t):
            if dialect == "mysql":
                return f"`{t}`"
            else:
                return f'"{t}"'

        with engine.connect() as conn:
            for table in allowed_tables:
                try:
                    columns = inspector.get_columns(table)
                    col_info = ", ".join(
                        f"{c['name']}({str(c['type'])})" for c in columns
                    )

                    rows = conn.execute(text(f"SELECT * FROM {quote_table(table)} LIMIT 3")).fetchall()
                    col_names = [c["name"] for c in columns]
                    sample_rows = [dict(zip(col_names, sanitize(list(row)))) for row in rows]
                    sample_text = "\n".join(str(r) for r in sample_rows) if sample_rows else "（无数据）"

                    schema_parts.append(
                        f"表名: {table}\n"
                        f"字段: {col_info}\n"
                        f"样本数据（前3行）:\n{sample_text}"
                    )
                except Exception as e:
                    schema_parts.append(f"表名: {table}\n（获取结构失败: {e}）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表结构失败: {e}")
    finally:
        engine.dispose()

    schema_context = "\n\n---\n\n".join(schema_parts)

    # 调用 LLM 生成注释
    system_prompt = """你是一位数据库业务分析专家。根据提供的数据库表结构和样本数据，为每张表的每个字段生成业务含义注释。

输出严格遵循以下 YAML 格式，不要输出任何其他内容：

tables:
  表名1:
    description: 表的业务描述
    columns:
      字段名1: 字段业务含义描述
      字段名2: 字段业务含义描述，如有枚举值请列出（如：1=启用, 0=禁用）
  表名2:
    description: 表的业务描述
    columns:
      字段名1: 字段业务含义描述

要求：
1. 根据字段名、类型和样本数据推断业务含义
2. 枚举类字段（status、type等）尽量列出可能的枚举值含义
3. 只输出 YAML，不要解释"""

    try:
        settings = load_settings(config_dir=CONFIG_DIR, env_file=ENV_PATH)
        llm = get_llm_client(settings["llm"])
        raw = llm.chat(
            [{"role": "system", "content": system_prompt},
             {"role": "user", "content": f"以下是数据库表结构和样本数据：\n\n{schema_context}"}],
            temperature=0.2,
        )

        # 去掉可能的 ```yaml ``` 包裹
        import re
        raw = re.sub(r"^```ya?ml\s*", "", raw.strip(), flags=re.IGNORECASE)
        raw = re.sub(r"\s*```$", "", raw.strip())

        # 验证是否合法 YAML
        yaml.safe_load(raw)
        return {"content": raw}

    except yaml.YAMLError as e:
        raise HTTPException(status_code=500, detail=f"LLM 返回的 YAML 格式有误: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {e}")
