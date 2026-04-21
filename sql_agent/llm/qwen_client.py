import os
from openai import OpenAI
from .base import BaseLLMClient


class QwenClient(BaseLLMClient):
    """
    通义千问客户端
    阿里云 DashScope 提供了 OpenAI 兼容接口，直接复用 OpenAI SDK
    """

    def __init__(self, config: dict):
        api_key = os.getenv("DASHSCOPE_API_KEY", config.get("api_key", ""))
        self._model = os.getenv("QWEN_MODEL", config.get("model", "qwen-plus"))
        self._max_tokens = config.get("max_tokens", 2048)

        # DashScope 的 OpenAI 兼容地址
        self._client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
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
