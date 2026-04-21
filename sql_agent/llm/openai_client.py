import os
from openai import OpenAI
from .base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """
    OpenAI 兼容接口客户端
    支持 OpenAI 官方接口、Azure OpenAI、本地部署的兼容接口（如 Ollama、vLLM）
    只需修改 OPENAI_BASE_URL 和 OPENAI_API_KEY 即可切换
    """

    def __init__(self, config: dict):
        api_key = os.getenv("OPENAI_API_KEY", config.get("api_key", ""))
        base_url = os.getenv("OPENAI_BASE_URL", config.get("base_url"))
        self._model = os.getenv("OPENAI_MODEL", config.get("model", "gpt-4o"))
        self._max_tokens = config.get("max_tokens", 2048)

        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,   # None 时使用 OpenAI 官方地址
        )

    def chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=self._max_tokens,
        )
        return response.choices[0].message.content.strip()

    def model_name(self) -> str:
        return self._model
