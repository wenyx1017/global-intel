"""
事件检测模块
Event Detection Module for Global Intelligence System

从文本中检测事件，支持多种事件类型和严重程度分级。
"""

import re
import yaml
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Event:
    """事件数据类"""
    event_type: str  # 事件类型
    label: str  # 事件标签
    category: str  # 事件类别
    severity: str  # 严重程度
    confidence: float  # 置信度
    text: str  # 原始文本
    entities: List[Dict] = field(default_factory=list)  # 相关实体
    trigger_keywords: List[str] = field(default_factory=list)  # 触发关键词
    timestamp: Optional[datetime] = None  # 时间戳
    location: Optional[str] = None  # 地点
    participants: List[str] = field(default_factory=list)  # 参与者


@dataclass
class DetectionRule:
    """检测规则"""
    event_type: str
    keywords: List[str]
    entity_combinations: List[List[str]]
    patterns: List[Dict]


class EventDetector:
    """事件检测器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化事件检测器
        
        Args:
            config_path: 配置文件路径，默认为 events.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "events.yaml"
        
        self.config_path = Path(config_path)
        self.event_types = []
        self.detection_rules = {}
        self.confidence_config = {}
        self.correlation_rules = {}
        
        self._load_config()
        self._compile_patterns()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.event_types = config.get('event_types', [])
        self.detection_rules = config.get('detection_rules', {})
        self.confidence_config = config.get('confidence', {})
        self.correlation_rules = config.get('correlation_rules', {})
    
    def _compile_patterns(self):
        """编译检测模式"""
        patterns_config = self.detection_rules.get('pattern_trigger', {}).get('patterns', {})
        
        for event_type, type_patterns in patterns_config.items():
            for i, pattern in enumerate(type_patterns):
                # 将占位符转换为正则表达式
                regex_pattern = pattern
                placeholders = re.findall(r'\{(\w+)\}', pattern)
                for placeholder in placeholders:
                    regex_pattern = regex_pattern.replace(f'{{{placeholder}}}', r'(.+?)')
                type_patterns[i] = {
                    'original': pattern,
                    'regex': re.compile(regex_pattern),
                    'placeholders': placeholders
                }
    
    def detect(self, text: str, entities: Optional[List[Dict]] = None) -> List[Event]:
        """
        从文本中检测事件
        
        Args:
            text: 输入文本
            entities: 已识别的实体列表（可选）
            
        Returns:
            检测到的事件列表
        """
        events = []
        
        # 遍历所有事件类型
        for event_type in self.event_types:
            type_name = event_type['name']
            type_label = event_type['label']
            category = event_type.get('category', 'general')
            
            # 关键词触发检测
            keyword_events = self._detect_by_keywords(text, event_type, entities)
            events.extend(keyword_events)
            
            # 实体组合触发检测
            entity_events = self._detect_by_entities(text, event_type, entities)
            events.extend(entity_events)
            
            # 模式触发检测
            pattern_events = self._detect_by_patterns(text, event_type, entities)
            events.extend(pattern_events)
        
        # 去重和排序
        events = self._deduplicate(events)
        events.sort(key=lambda e: e.confidence, reverse=True)
        
        return events
    
    def _detect_by_keywords(self, text: str, event_type: Dict, 
                           entities: Optional[List[Dict]] = None) -> List[Event]:
        """通过关键词检测事件"""
        events = []
        trigger_keywords = event_type.get('trigger_keywords', [])
        
        # 统计匹配的关键词数量
        matched_keywords = []
        for keyword in trigger_keywords:
            if keyword.lower() in text.lower():
                matched_keywords.append(keyword)
        
        # 如果没有匹配关键词，返回空
        if not matched_keywords:
            return events
        
        # 计算关键词触发的置信度
        keyword_weight = self.detection_rules.get('keyword_trigger', {}).get('weight', 0.4)
        base_confidence = self.confidence_config.get('base_confidence', 0.5)
        multi_boost = self.confidence_config.get('multi_keyword_boost', 0.1)
        
        # 多个关键词匹配增加置信度
        confidence = base_confidence + (len(matched_keywords) - 1) * multi_boost
        confidence = min(confidence, 1.0) * keyword_weight
        
        # 确定严重程度
        severity = self._determine_severity(text, event_type, entities)
        
        event = Event(
            event_type=event_type['name'],
            label=event_type['label'],
            category=event_type.get('category', 'general'),
            severity=severity,
            confidence=confidence,
            text=text,
            entities=entities or [],
            trigger_keywords=matched_keywords
        )
        events.append(event)
        
        return events
    
    def _detect_by_entities(self, text: str, event_type: Dict, 
                           entities: Optional[List[Dict]] = None) -> List[Event]:
        """通过实体组合检测事件"""
        events = []
        
        if not entities:
            return events
        
        # 获取该事件类型需要的实体组合
        entity_trigger = self.detection_rules.get('entity_trigger', {})
        required_combinations = entity_trigger.get('required_entity_combinations', {})
        
        event_name = event_type['name']
        combinations = required_combinations.get(event_name, [])
        
        if not combinations:
            return events
        
        # 检查是否满足任何实体组合
        entity_types = [e.get('type', '') for e in entities]
        
        for combination in combinations:
            if all(req_type in entity_types for req_type in combination):
                # 满足实体组合要求
                entity_weight = entity_trigger.get('weight', 0.4)
                entity_boost = self.confidence_config.get('entity_match_boost', 0.15)
                base_confidence = self.confidence_config.get('base_confidence', 0.5)
                
                confidence = min((base_confidence + entity_boost) * entity_weight, 1.0)
                severity = self._determine_severity(text, event_type, entities)
                
                # 提取位置信息
                location = self._extract_location(entities)
                
                # 提取参与者
                participants = self._extract_participants(entities)
                
                event = Event(
                    event_type=event_type['name'],
                    label=event_type['label'],
                    category=event_type.get('category', 'general'),
                    severity=severity,
                    confidence=confidence,
                    text=text,
                    entities=entities,
                    location=location,
                    participants=participants
                )
                events.append(event)
                break  # 满足一个组合即可
        
        return events
    
    def _detect_by_patterns(self, text: str, event_type: Dict, 
                           entities: Optional[List[Dict]] = None) -> List[Event]:
        """通过句法模式检测事件"""
        events = []
        
        pattern_trigger = self.detection_rules.get('pattern_trigger', {})
        patterns_config = pattern_trigger.get('patterns', {})
        
        event_name = event_type['name']
        patterns = patterns_config.get(event_name, [])
        
        if not patterns:
            return events
        
        for pattern_info in patterns:
            if 'regex' not in pattern_info:
                continue
            
            regex = pattern_info['regex']
            matches = regex.findall(text)
            
            if matches:
                pattern_weight = pattern_trigger.get('weight', 0.2)
                pattern_boost = self.confidence_config.get('pattern_match_boost', 0.15)
                base_confidence = self.confidence_config.get('base_confidence', 0.5)
                
                confidence = min((base_confidence + pattern_boost) * pattern_weight, 1.0)
                severity = self._determine_severity(text, event_type, entities)
                
                event = Event(
                    event_type=event_type['name'],
                    label=event_type['label'],
                    category=event_type.get('category', 'general'),
                    severity=severity,
                    confidence=confidence,
                    text=text,
                    entities=entities or [],
                    trigger_keywords=[pattern_info['original']]
                )
                events.append(event)
        
        return events
    
    def _determine_severity(self, text: str, event_type: Dict, 
                           entities: Optional[List[Dict]] = None) -> str:
        """确定事件严重程度"""
        severity_levels = event_type.get('severity_levels', [])
        
        if not severity_levels:
            return 'medium'
        
        # 检查文本中的严重程度指示词
        text_lower = text.lower()
        
        # critical 级别关键词
        critical_keywords = ['重大', '特别', '紧急', '严重', '灾难', '战争', '死亡', '伤亡']
        if any(kw in text_lower for kw in critical_keywords):
            return 'critical'
        
        # high 级别关键词
        high_keywords = ['重要', '显著', '大幅', '超预期', '制裁', '冲突']
        if any(kw in text_lower for kw in high_keywords):
            return 'high'
        
        # low 级别关键词
        low_keywords = ['常规', '一般', '普通', '轻微']
        if any(kw in text_lower for kw in low_keywords):
            return 'low'
        
        # 默认 medium
        return 'medium'
    
    def _extract_location(self, entities: List[Dict]) -> Optional[str]:
        """从实体中提取位置信息"""
        for entity in entities:
            if entity.get('type') == 'GPE':
                return entity.get('text')
        return None
    
    def _extract_participants(self, entities: List[Dict]) -> List[str]:
        """从实体中提取参与者"""
        participants = []
        participant_types = ['PERSON', 'GOV_ORG', 'ORG']
        
        for entity in entities:
            if entity.get('type') in participant_types:
                participants.append(entity.get('text', ''))
        
        return participants
    
    def _deduplicate(self, events: List[Event]) -> List[Event]:
        """去重事件"""
        seen = set()
        unique_events = []
        
        for event in events:
            # 创建去重键
            key = (event.event_type, event.text[:100])
            
            if key not in seen:
                seen.add(key)
                unique_events.append(event)
            else:
                # 如果已存在，保留置信度更高的
                existing = next((e for e in unique_events 
                               if (e.event_type, e.text[:100]) == key), None)
                if existing and event.confidence > existing.confidence:
                    existing.confidence = event.confidence
        
        return unique_events
    
    def filter_by_severity(self, events: List[Event], 
                          min_severity: str = 'medium') -> List[Event]:
        """
        根据严重程度过滤事件
        
        Args:
            events: 事件列表
            min_severity: 最小严重程度 (low, medium, high, critical)
            
        Returns:
            过滤后的事件列表
        """
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        min_level = severity_order.get(min_severity, 1)
        
        return [e for e in events if severity_order.get(e.severity, 0) >= min_level]
    
    def filter_by_confidence(self, events: List[Event], 
                            threshold: Optional[float] = None) -> List[Event]:
        """
        根据置信度过滤事件
        
        Args:
            events: 事件列表
            threshold: 置信度阈值，默认为配置中的 min_threshold
            
        Returns:
            过滤后的事件列表
        """
        if threshold is None:
            threshold = self.confidence_config.get('min_threshold', 0.5)
        
        return [e for e in events if e.confidence >= threshold]
    
    def filter_by_category(self, events: List[Event], 
                          category: str) -> List[Event]:
        """
        根据类别过滤事件
        
        Args:
            events: 事件列表
            category: 事件类别
            
        Returns:
            过滤后的事件列表
        """
        return [e for e in events if e.category == category]
    
    def get_event_types(self) -> List[str]:
        """获取所有事件类型"""
        return [et['name'] for et in self.event_types]
    
    def get_event_labels(self) -> Dict[str, str]:
        """获取事件类型到标签的映射"""
        return {et['name']: et['label'] for et in self.event_types}
    
    def correlate_events(self, events: List[Event]) -> List[List[Event]]:
        """
        关联相关事件
        
        Args:
            events: 事件列表
            
        Returns:
            关联的事件组列表
        """
        if not events:
            return []
        
        correlated_groups = []
        used = set()
        
        for i, event1 in enumerate(events):
            if i in used:
                continue
            
            group = [event1]
            used.add(i)
            
            for j, event2 in enumerate(events[i+1:], i+1):
                if j in used:
                    continue
                
                if self._are_events_correlated(event1, event2):
                    group.append(event2)
                    used.add(j)
            
            if len(group) > 1:
                correlated_groups.append(group)
        
        return correlated_groups
    
    def _are_events_correlated(self, event1: Event, event2: Event) -> bool:
        """判断两个事件是否相关"""
        # 类型相同
        if event1.event_type != event2.event_type:
            return False
        
        # 位置相关
        if self.correlation_rules.get('location_correlation', False):
            if event1.location and event2.location:
                if event1.location == event2.location:
                    return True
        
        # 实体相关
        if self.correlation_rules.get('entity_correlation', False):
            entities1 = {e.get('text') for e in event1.entities}
            entities2 = {e.get('text') for e in event2.entities}
            if entities1 & entities2:  # 有共同实体
                return True
        
        return False


def detect_events(text: str, entities: Optional[List[Dict]] = None,
                 config_path: Optional[str] = None) -> List[Event]:
    """
    便捷函数：从文本中检测事件
    
    Args:
        text: 输入文本
        entities: 已识别的实体列表（可选）
        config_path: 配置文件路径（可选）
        
    Returns:
        检测到的事件列表
    """
    detector = EventDetector(config_path)
    return detector.detect(text, entities)


# 使用示例
if __name__ == "__main__":
    # 示例文本
    texts = [
        "国务院发布十四五规划，该规划将影响能源行业。",
        "张三被任命为财政部长，这是重要人事变动。",
        "中国一季度 GDP 同比增长 5.2%，超预期。",
        "中美举行高层会谈，讨论贸易问题。",
        "日本发生 7.0 级地震，造成人员伤亡。"
    ]
    
    # 示例实体
    all_entities = [
        {"text": "国务院", "type": "GOV_ORG"},
        {"text": "十四五规划", "type": "LAW_POLICY"},
        {"text": "能源行业", "type": "ORG"},
        {"text": "张三", "type": "PERSON"},
        {"text": "财政部", "type": "GOV_ORG"},
        {"text": "中国", "type": "GPE"},
        {"text": "GDP", "type": "INDICATOR"},
        {"text": "美国", "type": "GPE"},
        {"text": "日本", "type": "GPE"},
        {"text": "地震", "type": "EVENT"},
    ]
    
    # 检测事件
    detector = EventDetector()
    
    print("事件检测结果:")
    print("=" * 60)
    
    for i, text in enumerate(texts):
        print(f"\n文本 {i+1}: {text}")
        
        # 选择相关实体
        entities = all_entities[:3] if i == 0 else all_entities[3:6] if i == 1 else all_entities
        
        events = detector.detect(text, entities)
        high_conf_events = detector.filter_by_confidence(events, threshold=0.5)
        
        if high_conf_events:
            for event in high_conf_events:
                print(f"  事件类型：{event.label}")
                print(f"  严重程度：{event.severity}")
                print(f"  置信度：{event.confidence:.2f}")
                print(f"  触发词：{', '.join(event.trigger_keywords)}")
                if event.location:
                    print(f"  地点：{event.location}")
        else:
            print("  未检测到事件")
