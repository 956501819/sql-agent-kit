import os
from openai import OpenAI
from .base import BaseLLMClient


class BailianClient(BaseLLMClient):
    """
    阿里云百炼平台客户端
    百炼使用与 DashScope 相同的 OpenAI 兼容接口，通过独立的 BAILIAN_API_KEY 鉴权
    支持模型：qwen-plus、qwen-max、qwen-turbo、qwen-long 等
    控制台：https://bailian.console.aliyun.com/
    """

    BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, config: dict):
        api_key = os.getenv("BAILIAN_API_KEY", config.get("api_key", ""))
        self._model = os.getenv("BAILIAN_MODEL", config.get("model", "qwen-plus"))
        self._max_tokens = config.get("max_tokens", 2048)

        self._client = OpenAI(
            api_key=api_key,
            base_url=self.BASE_URL,
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
