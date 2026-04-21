import os
from openai import OpenAI
from .base import BaseLLMClient


class SiliconFlowClient(BaseLLMClient):
    """
    硅基流动客户端
    提供 OpenAI 兼容接口，支持 Qwen、DeepSeek、GLM 等主流开源模型
    """

    def __init__(self, config: dict):
        api_key = os.getenv("SILICONFLOW_API_KEY", config.get("api_key", ""))
        self._model = os.getenv("SILICONFLOW_MODEL", config.get("model", "Qwen/Qwen2.5-72B-Instruct"))
        self._max_tokens = config.get("max_tokens", 2048)

        self._client = OpenAI(
            api_key=api_key,
            base_url="https://api.siliconflow.cn/v1",
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
