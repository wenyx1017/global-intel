#!/usr/bin/env python3
"""
情报分析任务模块
包含图谱验证、关联验证、报告生成三大核心功能
"""

import json
import time
import yaml
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from provider import (
    LLMProvider, ModelConfig, ChatMessage, ModelResponse,
    ProviderFactory, ModelProvider
)


@dataclass
class Entity:
    """知识图谱实体"""
    id: str
    name: str
    type: str
    properties: Dict[str, Any]


@dataclass
class Relation:
    """知识图谱关系"""
    id: str
    source: str  # 实体 ID
    target: str  # 实体 ID
    type: str
    properties: Dict[str, Any]


@dataclass
class VerificationResult:
    """验证结果"""
    is_valid: bool
    confidence: float  # 0-1
    issues: List[str]
    suggestions: List[str]
    evidence: str


@dataclass
class AnalysisReport:
    """分析报告"""
    report_type: str  # daily/weekly
    generated_at: str
    period_start: str
    period_end: str
    summary: str
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    cost: float
    token_usage: Dict[str, int]


class IntelligenceAnalyzer:
    """情报分析器"""
    
    def __init__(self, config_path: str):
        """
        初始化分析器
        
        Args:
            config_path: 大模型配置文件路径 (llm_config.yaml)
        """
        self.config = self._load_config(config_path)
        self.provider = self._init_provider()
        self.daily_budget = self.config.get("budget", {}).get("daily_limit", 10.0)
        self.min_interval = self.config.get("rate_limit", {}).get("min_interval", 3600)
        self.max_daily_calls = self.config.get("rate_limit", {}).get("max_daily_calls", 24)
        
        # 状态跟踪
        self.state_file = Path(config_path).parent / "analyzer_state.json"
        self.state = self._load_state()
    
    def _load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _init_provider(self) -> LLMProvider:
        """初始化大模型提供商"""
        llm_config = self.config.get("llm", {})
        config = ModelConfig(
            provider=ModelProvider(llm_config.get("provider", "openai")),
            model_name=llm_config.get("model", "gpt-4o-mini"),
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("base_url"),
            max_tokens=llm_config.get("max_tokens", 4096),
            temperature=llm_config.get("temperature", 0.7)
        )
        return ProviderFactory.create_provider(config)
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "last_call_timestamp": 0,
            "calls_today": 0,
            "spent_today": 0.0,
            "today_date": datetime.now().strftime("%Y-%m-%d")
        }
    
    def _save_state(self):
        """保存状态"""
        # 检查是否需要重置每日计数
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state["today_date"] != today:
            self.state["calls_today"] = 0
            self.state["spent_today"] = 0.0
            self.state["today_date"] = today
        
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _check_rate_limit(self) -> Tuple[bool, str]:
        """检查频率限制"""
        self._save_state()  # 更新每日计数
        
        # 检查每日调用次数
        if self.state["calls_today"] >= self.max_daily_calls:
            return False, f"已达到每日最大调用次数 ({self.max_daily_calls})"
        
        # 检查每日预算
        if self.state["spent_today"] >= self.daily_budget:
            return False, f"已达到每日预算 (${self.daily_budget:.2f})"
        
        # 检查调用间隔
        current_time = time.time()
        time_since_last = current_time - self.state["last_call_timestamp"]
        if time_since_last < self.min_interval:
            remaining = int(self.min_interval - time_since_last)
            return False, f"需要等待 {remaining} 秒后才能再次调用"
        
        return True, "OK"
    
    def _update_state(self, cost: float):
        """更新状态"""
        self.state["last_call_timestamp"] = time.time()
        self.state["calls_today"] += 1
        self.state["spent_today"] += cost
        self._save_state()
    
    def verify_knowledge_graph(
        self,
        entities: List[Entity],
        relations: List[Relation],
        context: str = ""
    ) -> VerificationResult:
        """
        图谱验证 - 检测知识图谱的事实错误
        
        Args:
            entities: 实体列表
            relations: 关系列表
            context: 额外上下文信息
        
        Returns:
            VerificationResult: 验证结果
        """
        # 检查频率限制
        allowed, message = self._check_rate_limit()
        if not allowed:
            raise RateLimitError(message)
        
        # 构建提示词
        entities_json = json.dumps([asdict(e) for e in entities], ensure_ascii=False, indent=2)
        relations_json = json.dumps([asdict(r) for r in relations], ensure_ascii=False, indent=2)
        
        prompt = f"""
你是一个知识图谱验证专家。请分析以下知识图谱的准确性：

## 实体列表
{entities_json}

## 关系列表
{relations_json}

{f"## 上下文信息\n{context}" if context else ""}

请执行以下验证：
1. 检查每个实体的事实准确性
2. 检查关系是否符合现实逻辑
3. 识别可能的错误或矛盾
4. 提供证据支持你的判断

请以 JSON 格式返回结果：
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["问题 1", "问题 2", ...],
    "suggestions": ["建议 1", "建议 2", ...],
    "evidence": "详细证据说明"
}}
"""
        
        messages = [ChatMessage(role="user", content=prompt)]
        
        # 调用大模型
        response = self.provider.chat(messages)
        self._update_state(response.cost)
        
        # 解析响应
        try:
            # 提取 JSON 部分
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result_dict = json.loads(content)
            return VerificationResult(
                is_valid=result_dict.get("is_valid", False),
                confidence=result_dict.get("confidence", 0.0),
                issues=result_dict.get("issues", []),
                suggestions=result_dict.get("suggestions", []),
                evidence=result_dict.get("evidence", "")
            )
        except Exception as e:
            # 解析失败时返回保守结果
            return VerificationResult(
                is_valid=False,
                confidence=0.5,
                issues=[f"解析验证结果时出错：{str(e)}"],
                suggestions=["请手动检查知识图谱"],
                evidence=response.content
            )
    
    def verify_relation_validity(
        self,
        source_entity: Entity,
        target_entity: Entity,
        relation_type: str,
        context: str = ""
    ) -> VerificationResult:
        """
        关联验证 - 验证实体间关联的合理性
        
        Args:
            source_entity: 源实体
            target_entity: 目标实体
            relation_type: 关系类型
            context: 额外上下文
        
        Returns:
            VerificationResult: 验证结果
        """
        # 检查频率限制
        allowed, message = self._check_rate_limit()
        if not allowed:
            raise RateLimitError(message)
        
        prompt = f"""
你是一个关联关系验证专家。请分析以下实体间关系的合理性：

## 源实体
- 名称：{source_entity.name}
- 类型：{source_entity.type}
- 属性：{json.dumps(source_entity.properties, ensure_ascii=False)}

## 目标实体
- 名称：{target_entity.name}
- 类型：{target_entity.type}
- 属性：{json.dumps(target_entity.properties, ensure_ascii=False)}

## 关系类型
{relation_type}

{f"## 上下文信息\n{context}" if context else ""}

请分析：
1. 这种关系在现实中是否合理
2. 是否存在逻辑矛盾
3. 需要什么证据来支持这种关系
4. 可能的替代解释

请以 JSON 格式返回结果：
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "issues": ["问题 1", "问题 2", ...],
    "suggestions": ["建议 1", "建议 2", ...],
    "evidence": "详细证据说明"
}}
"""
        
        messages = [ChatMessage(role="user", content=prompt)]
        response = self.provider.chat(messages)
        self._update_state(response.cost)
        
        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result_dict = json.loads(content)
            return VerificationResult(
                is_valid=result_dict.get("is_valid", False),
                confidence=result_dict.get("confidence", 0.0),
                issues=result_dict.get("issues", []),
                suggestions=result_dict.get("suggestions", []),
                evidence=result_dict.get("evidence", "")
            )
        except Exception as e:
            return VerificationResult(
                is_valid=False,
                confidence=0.5,
                issues=[f"解析验证结果时出错：{str(e)}"],
                suggestions=["请手动检查关联关系"],
                evidence=response.content
            )
    
    def generate_report(
        self,
        report_type: str,
        data: Dict[str, Any],
        period_days: int = 1
    ) -> AnalysisReport:
        """
        报告生成 - 生成每日/每周情报报告
        
        Args:
            report_type: 报告类型 (daily/weekly)
            data: 分析数据
            period_days: 周期天数
        
        Returns:
            AnalysisReport: 分析报告
        """
        # 检查频率限制
        allowed, message = self._check_rate_limit()
        if not allowed:
            raise RateLimitError(message)
        
        now = datetime.now()
        period_start = (now - timedelta(days=period_days)).strftime("%Y-%m-%d")
        period_end = now.strftime("%Y-%m-%d")
        
        data_json = json.dumps(data, ensure_ascii=False, indent=2)
        
        prompt = f"""
你是一个情报分析专家。请根据以下数据生成{report_type}情报报告：

## 分析数据
{data_json}

## 报告周期
{period_start} 至 {period_end}

请生成包含以下内容的报告：
1. 执行摘要（200-300 字）
2. 关键发现（3-5 条，每条包含重要性和证据）
3. 行动建议（2-4 条具体建议）

请以 JSON 格式返回：
{{
    "summary": "执行摘要",
    "findings": [
        {{"title": "发现标题", "importance": "high/medium/low", "description": "详细描述", "evidence": "证据"}},
        ...
    ],
    "recommendations": ["建议 1", "建议 2", ...]
}}
"""
        
        messages = [ChatMessage(role="user", content=prompt)]
        response = self.provider.chat(messages)
        self._update_state(response.cost)
        
        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            result_dict = json.loads(content)
            return AnalysisReport(
                report_type=report_type,
                generated_at=now.isoformat(),
                period_start=period_start,
                period_end=period_end,
                summary=result_dict.get("summary", ""),
                findings=result_dict.get("findings", []),
                recommendations=result_dict.get("recommendations", []),
                cost=response.cost,
                token_usage=response.usage
            )
        except Exception as e:
            return AnalysisReport(
                report_type=report_type,
                generated_at=now.isoformat(),
                period_start=period_start,
                period_end=period_end,
                summary=f"报告生成失败：{str(e)}",
                findings=[],
                recommendations=["请手动分析数据"],
                cost=response.cost,
                token_usage=response.usage
            )
    
    def get_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        self._save_state()
        return {
            "provider": self.config.get("llm", {}).get("provider", "unknown"),
            "model": self.config.get("llm", {}).get("model", "unknown"),
            "daily_budget": self.daily_budget,
            "spent_today": self.state["spent_today"],
            "calls_today": self.state["calls_today"],
            "max_daily_calls": self.max_daily_calls,
            "min_interval_seconds": self.min_interval,
            "last_call": datetime.fromtimestamp(self.state["last_call_timestamp"]).isoformat() if self.state["last_call_timestamp"] > 0 else "Never"
        }


class RateLimitError(Exception):
    """频率限制错误"""
    pass


# 使用示例
if __name__ == "__main__":
    # 初始化分析器
    analyzer = IntelligenceAnalyzer("llm_config.yaml")
    
    # 查看状态
    print("分析器状态:", json.dumps(analyzer.get_status(), indent=2, ensure_ascii=False))
    
    # 示例：图谱验证
    entities = [
        Entity(id="1", name="苹果公司", type="Organization", properties={"industry": "科技"}),
        Entity(id="2", name="Tim Cook", type="Person", properties={"role": "CEO"})
    ]
    relations = [
        Relation(id="r1", source="2", target="1", type="WORKS_FOR", properties={})
    ]
    
    result = analyzer.verify_knowledge_graph(entities, relations)
    print("\n图谱验证结果:")
    print(f"  有效性：{result.is_valid}")
    print(f"  置信度：{result.confidence}")
    print(f"  问题：{result.issues}")
