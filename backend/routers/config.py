import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")


def _read_env() -> dict:
    env = {}
    if not os.path.exists(_ENV_PATH):
        return env
    with open(_ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def _write_env(env: dict):
    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Update existing keys, collect new ones
    updated_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in env:
                new_lines.append(f"{k}={env[k]}\n")
                updated_keys.add(k)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    for k, v in env.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(_ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


@router.get("/config")
async def get_config():
    env = _read_env()
    return {
        "provider": env.get("LLM_PROVIDER", "siliconflow"),
        "openai": {
            "api_key": env.get("OPENAI_API_KEY", ""),
            "base_url": env.get("OPENAI_BASE_URL", ""),
            "model": env.get("OPENAI_MODEL", "gpt-4o"),
        },
        "qwen": {
            "api_key": env.get("DASHSCOPE_API_KEY", ""),
            "model": env.get("QWEN_MODEL", "qwen-plus"),
        },
        "siliconflow": {
            "api_key": env.get("SILICONFLOW_API_KEY", ""),
            "model": env.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-72B-Instruct"),
        },
        "bailian": {
            "api_key": env.get("BAILIAN_API_KEY", ""),
            "model": env.get("BAILIAN_MODEL", "qwen-plus"),
        },
        "db": {
            "type": env.get("DB_TYPE", "mysql"),
            "host": env.get("DB_HOST", "127.0.0.1"),
            "port": env.get("DB_PORT", "3306"),
            "user": env.get("DB_USER", ""),
            "password": env.get("DB_PASSWORD", ""),
            "name": env.get("DB_NAME", ""),
            "sqlite_path": env.get("DB_SQLITE_PATH", ""),
        },
    }


class ConfigPayload(BaseModel):
    provider: str = ""
    openai: dict = {}
    qwen: dict = {}
    siliconflow: dict = {}
    bailian: dict = {}
    db: dict = {}


@router.post("/config")
async def save_config(payload: ConfigPayload):
    from backend.services.agent_service import reset_agent

    updates = {}
    if payload.provider:
        updates["LLM_PROVIDER"] = payload.provider
    if payload.openai.get("api_key"):
        updates["OPENAI_API_KEY"] = payload.openai["api_key"]
    if payload.openai.get("base_url"):
        updates["OPENAI_BASE_URL"] = payload.openai["base_url"]
    if payload.openai.get("model"):
        updates["OPENAI_MODEL"] = payload.openai["model"]
    if payload.qwen.get("api_key"):
        updates["DASHSCOPE_API_KEY"] = payload.qwen["api_key"]
    if payload.qwen.get("model"):
        updates["QWEN_MODEL"] = payload.qwen["model"]
    if payload.siliconflow.get("api_key"):
        updates["SILICONFLOW_API_KEY"] = payload.siliconflow["api_key"]
    if payload.siliconflow.get("model"):
        updates["SILICONFLOW_MODEL"] = payload.siliconflow["model"]
    if payload.bailian.get("api_key"):
        updates["BAILIAN_API_KEY"] = payload.bailian["api_key"]
    if payload.bailian.get("model"):
        updates["BAILIAN_MODEL"] = payload.bailian["model"]

    db = payload.db
    for k, env_k in [
        ("type", "DB_TYPE"), ("host", "DB_HOST"), ("port", "DB_PORT"),
        ("user", "DB_USER"), ("password", "DB_PASSWORD"),
        ("name", "DB_NAME"), ("sqlite_path", "DB_SQLITE_PATH"),
    ]:
        if db.get(k) is not None:
            updates[env_k] = str(db[k])

    _write_env(updates)
    reset_agent()
    return {"message": "配置已保存"}


class TestLLMRequest(BaseModel):
    provider: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""


@router.post("/config/test-llm")
async def test_llm(req: TestLLMRequest):
    import asyncio

    def _do_test():
        from openai import OpenAI
        if req.provider in ("openai", "siliconflow"):
            base = req.base_url or ("https://api.siliconflow.cn/v1" if req.provider == "siliconflow" else None)
            client = OpenAI(api_key=req.api_key, base_url=base)
            client.chat.completions.create(
                model=req.model or "Qwen/Qwen2.5-7B-Instruct",
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
        elif req.provider in ("qwen", "bailian"):
            import dashscope
            dashscope.api_key = req.api_key
            from dashscope import Generation
            Generation.call(model=req.model or "qwen-plus", messages=[{"role": "user", "content": "hi"}])

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_test)
        return {"success": True, "message": "连接成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}


class TestDBRequest(BaseModel):
    type: str = "mysql"
    host: str = "127.0.0.1"
    port: str = "3306"
    user: str = ""
    password: str = ""
    name: str = ""
    sqlite_path: str = ""


@router.post("/config/test-db")
async def test_db(req: TestDBRequest):
    import asyncio

    def _do_test():
        from sqlalchemy import create_engine, text
        if req.type == "sqlite":
            url = f"sqlite:///{req.sqlite_path}"
            connect_args = {}
        elif req.type == "postgresql":
            url = f"postgresql+psycopg2://{req.user}:{req.password}@{req.host}:{req.port}/{req.name}"
            connect_args = {"connect_timeout": 5}
        else:
            url = f"mysql+pymysql://{req.user}:{req.password}@{req.host}:{req.port}/{req.name}"
            connect_args = {"connect_timeout": 5}
        engine = create_engine(url, connect_args=connect_args)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _do_test)
        return {"success": True, "message": "数据库连接成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}
