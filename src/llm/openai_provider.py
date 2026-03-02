#!/usr/bin/env python3
"""
OpenAI API 实现
支持 GPT-3.5/GPT-4/GPT-4o 等模型
"""

import json
import time
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from provider import (
    LLMProvider, ModelConfig, ChatMessage, ModelResponse, ModelProvider
)


# OpenAI 模型定价（每 1000 tokens，美元）
OPENAI_PRICES = {
    "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
    "gpt-4o": {"prompt": 0.005, "completion": 0.015},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
}


class OpenAIProvider(LLMProvider):
    """OpenAI 提供商实现"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def client(self):
        """懒加载 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url or "https://api.openai.com/v1",
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError("请安装 openai 库：pip install openai")
        return self._client
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> ModelResponse:
        """发送聊天请求"""
        # 转换消息格式
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # 调用 API
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=openai_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        
        # 提取响应
        choice = response.choices[0]
        usage = response.usage
        
        # 计算成本
        cost = self.calculate_cost(usage.prompt_tokens, usage.completion_tokens)
        
        return ModelResponse(
            content=choice.message.content,
            model=response.model,
            usage={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            finish_reason=choice.finish_reason,
            cost=cost
        )
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算调用成本"""
        prices = OPENAI_PRICES.get(self.config.model_name, OPENAI_PRICES["gpt-4o-mini"])
        prompt_cost = (prompt_tokens / 1000) * prices["prompt"]
        completion_cost = (completion_tokens / 1000) * prices["completion"]
        return prompt_cost + completion_cost
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "openai",
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "context_window": self._get_context_window(),
            "pricing": OPENAI_PRICES.get(self.config.model_name, "unknown")
        }
    
    def _get_context_window(self) -> int:
        """获取模型上下文窗口大小"""
        context_windows = {
            "gpt-3.5-turbo": 16385,
            "gpt-4": 8192,
            "gpt-4-turbo": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
        }
        return context_windows.get(self.config.model_name, 128000)


# 使用示例
if __name__ == "__main__":
    # 配置示例
    config = ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o-mini",
        api_key="your-api-key-here"
    )
    
    provider = OpenAIProvider(config)
    
    # 测试聊天
    messages = [
        ChatMessage(role="system", content="你是一个有帮助的助手。"),
        ChatMessage(role="user", content="你好！")
    ]
    
    response = provider.chat(messages)
    print(f"响应：{response.content}")
    print(f"成本：${response.cost:.6f}")
    print(f"Token 使用：{response.usage}")
