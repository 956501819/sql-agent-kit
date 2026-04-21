from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMClient(ABC):
    """LLM 客户端抽象基类，统一接口，方便切换不同模型"""

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        """
        发送对话消息，返回模型回复文本
        :param messages: [{"role": "system/user/assistant", "content": "..."}]
        :param temperature: 温度参数
        :return: 模型回复的纯文本
        """
        ...

    @abstractmethod
    def model_name(self) -> str:
        """返回当前使用的模型名称"""
        ...
