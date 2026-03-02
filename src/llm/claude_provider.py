#!/usr/bin/env python3
"""
Anthropic Claude API 实现
支持 Claude 3 系列模型
"""

import json
from typing import List, Dict, Any
from provider import LLMProvider, ModelConfig, ChatMessage, ModelResponse, ModelProvider


# Claude 模型定价（每 1000 tokens，美元）
CLAUDE_PRICES = {
    "claude-3-5-sonnet-20241022": {"prompt": 0.003, "completion": 0.015},
    "claude-3-sonnet-20240229": {"prompt": 0.003, "completion": 0.015},
    "claude-3-opus-20240229": {"prompt": 0.015, "completion": 0.075},
    "claude-3-haiku-20240307": {"prompt": 0.00025, "completion": 0.00125},
}


class ClaudeProvider(LLMProvider):
    """Claude 提供商实现"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def client(self):
        """懒加载 Claude 客户端"""
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.config.api_key)
            except ImportError:
                raise ImportError("请安装 anthropic 库：pip install anthropic")
        return self._client
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> ModelResponse:
        """发送聊天请求"""
        # 分离系统消息和其他消息
        system_message = ""
        chat_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                chat_messages.append({
                    "role": "user" if msg.role == "user" else "assistant",
                    "content": msg.content
                })
        
        # 调用 API
        response = self.client.messages.create(
            model=self.config.model_name,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            system=system_message if system_message else None,
            messages=chat_messages,
        )
        
        # 计算成本
        cost = self.calculate_cost(
            response.usage.input_tokens,
            response.usage.output_tokens
        )
        
        return ModelResponse(
            content=response.content[0].text,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            finish_reason=response.stop_reason,
            cost=cost
        )
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算调用成本"""
        prices = CLAUDE_PRICES.get(self.config.model_name, CLAUDE_PRICES["claude-3-5-sonnet-20241022"])
        prompt_cost = (prompt_tokens / 1000) * prices["prompt"]
        completion_cost = (completion_tokens / 1000) * prices["completion"]
        return prompt_cost + completion_cost
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "claude",
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "context_window": self._get_context_window(),
            "pricing": CLAUDE_PRICES.get(self.config.model_name, "unknown")
        }
    
    def _get_context_window(self) -> int:
        """获取模型上下文窗口大小"""
        context_windows = {
            "claude-3-5-sonnet-20241022": 200000,
            "claude-3-sonnet-20240229": 200000,
            "claude-3-opus-20240229": 200000,
            "claude-3-haiku-20240307": 200000,
        }
        return context_windows.get(self.config.model_name, 200000)
