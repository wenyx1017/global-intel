#!/usr/bin/env python3
"""
大模型抽象接口层
支持 OpenAI/GPT/Claude/通义千问等主流大模型
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class ModelProvider(Enum):
    """支持的模型提供商"""
    OPENAI = "openai"
    CLAUDE = "claude"
    QWEN = "qwen"  # 通义千问
    GPT = "gpt"


@dataclass
class ModelConfig:
    """模型配置"""
    provider: ModelProvider
    model_name: str
    api_key: str
    base_url: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 60


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str


@dataclass
class ModelResponse:
    """模型响应"""
    content: str
    model: str
    usage: Dict[str, int]  # prompt_tokens, completion_tokens, total_tokens
    finish_reason: str
    cost: float  # 本次调用成本（美元）


class LLMProvider(ABC):
    """大模型提供商抽象基类"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
    
    @abstractmethod
    def chat(self, messages: List[ChatMessage], **kwargs) -> ModelResponse:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """计算调用成本"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    def validate_budget(self, daily_budget: float, spent_today: float) -> bool:
        """验证是否超出预算"""
        return spent_today < daily_budget
    
    def validate_rate_limit(self, last_call_timestamp: float, min_interval: int) -> bool:
        """验证调用频率限制"""
        import time
        current_time = time.time()
        return (current_time - last_call_timestamp) >= min_interval


class ProviderFactory:
    """提供商工厂"""
    
    @staticmethod
    def create_provider(config: ModelConfig) -> LLMProvider:
        """根据配置创建对应的提供商实例"""
        if config.provider == ModelProvider.OPENAI or config.provider == ModelProvider.GPT:
            from openai_provider import OpenAIProvider
            return OpenAIProvider(config)
        elif config.provider == ModelProvider.CLAUDE:
            from claude_provider import ClaudeProvider
            return ClaudeProvider(config)
        elif config.provider == ModelProvider.QWEN:
            from qwen_provider import QwenProvider
            return QwenProvider(config)
        else:
            raise ValueError(f"不支持的提供商：{config.provider}")
