#!/usr/bin/env python3
"""
阿里云通义千问 (Qwen) API 实现
支持 DashScope 兼容模式
"""

import json
from typing import List, Dict, Any
from provider import LLMProvider, ModelConfig, ChatMessage, ModelResponse, ModelProvider


# 通义千问模型定价（每 1000 tokens，人民币，转换为美元）
# 汇率参考：1 USD ≈ 7.2 CNY
QWEN_PRICES_CNY = {
    "qwen-plus": {"prompt": 0.004, "completion": 0.012},
    "qwen-turbo": {"prompt": 0.002, "completion": 0.006},
    "qwen-max": {"prompt": 0.04, "completion": 0.12},
    "qwen-max-longcontext": {"prompt": 0.04, "completion": 0.12},
}

USD_CNY_RATE = 7.2


class QwenProvider(LLMProvider):
    """通义千问提供商实现"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self._client = None
    
    @property
    def client(self):
        """懒加载 DashScope 客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                # 使用 OpenAI 兼容模式访问 DashScope
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1",
                    timeout=self.config.timeout
                )
            except ImportError:
                raise ImportError("请安装 openai 库：pip install openai")
        return self._client
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> ModelResponse:
        """发送聊天请求"""
        # 转换消息格式
        qwen_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        # 调用 API（使用 OpenAI 兼容接口）
        response = self.client.chat.completions.create(
            model=self.config.model_name,
            messages=qwen_messages,
            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
            temperature=kwargs.get("temperature", self.config.temperature),
        )
        
        # 提取响应
        choice = response.choices[0]
        usage = response.usage
        
        # 计算成本（从人民币转换为美元）
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
        """计算调用成本（美元）"""
        prices = QWEN_PRICES_CNY.get(self.config.model_name, QWEN_PRICES_CNY["qwen-plus"])
        prompt_cost_cny = (prompt_tokens / 1000) * prices["prompt"]
        completion_cost_cny = (completion_tokens / 1000) * prices["completion"]
        # 转换为美元
        total_cny = prompt_cost_cny + completion_cost_cny
        return total_cny / USD_CNY_RATE
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "qwen",
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "context_window": self._get_context_window(),
            "pricing_usd": {
                model: {
                    "prompt": prices["prompt"] / USD_CNY_RATE,
                    "completion": prices["completion"] / USD_CNY_RATE
                }
                for model, prices in QWEN_PRICES_CNY.items()
            }
        }
    
    def _get_context_window(self) -> int:
        """获取模型上下文窗口大小"""
        context_windows = {
            "qwen-plus": 131072,
            "qwen-turbo": 131072,
            "qwen-max": 32768,
            "qwen-max-longcontext": 245760,
        }
        return context_windows.get(self.config.model_name, 131072)
