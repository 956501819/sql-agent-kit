from .base import BaseLLMClient
from .openai_client import OpenAIClient
from .qwen_client import QwenClient
from .siliconflow_client import SiliconFlowClient
from .bailian_client import BailianClient


def get_llm_client(settings: dict) -> BaseLLMClient:
    """根据配置返回对应的 LLM 客户端"""
    provider = settings.get("provider", "openai")
    if provider == "qwen":
        return QwenClient(settings.get("qwen", {}))
    if provider == "siliconflow":
        return SiliconFlowClient(settings.get("siliconflow", {}))
    if provider == "bailian":
        return BailianClient(settings.get("bailian", {}))
    return OpenAIClient(settings.get("openai", {}))
