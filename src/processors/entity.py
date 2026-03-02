#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实体识别模块 (Entity Recognition)
==================================
基于 spaCy 的多语言命名实体识别

实体类型:
- GPE: 国家/地区
- GOV_ORG: 政府机构
- ORG: 公司/组织
- PERSON: 人物
- EVENT: 事件
- LAW_POLICY: 政策/法规
"""

import re
import yaml
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

# 尝试导入 spaCy
try:
    import spacy
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logging.warning("spaCy not installed. Install with: pip install spacy spacy-transformers")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """实体数据类"""
    text: str
    label: str
    label_name: str
    start: int
    end: int
    confidence: float = 1.0
    source: str = 'spacy'  # spacy, rule, custom
    normalized: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'label': self.label,
            'label_name': self.label_name,
            'start': self.start,
            'end': self.end,
            'confidence': self.confidence,
            'source': self.source,
            'normalized': self.normalized,
            'metadata': self.metadata
        }


@dataclass
class EntityRecognitionResult:
    """实体识别结果"""
    original_text: str
    entities: List[Entity] = field(default_factory=list)
    entity_counts: Dict[str, int] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_text': self.original_text,
            'entities': [e.to_dict() for e in self.entities],
            'entity_counts': self.entity_counts,
            'processing_time_ms': self.processing_time_ms,
            'timestamp': self.timestamp.isoformat()
        }


class EntityNormalizer:
    """
    实体标准化器
    
    根据 entities.yaml 中的规则进行实体名称标准化
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化标准化器
        
        Args:
            config_path: entities.yaml 路径
        """
        self.config_path = config_path
        self.normalization_rules = {}
        self.alias_map = {}
        
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, config_path: str):
        """加载配置文件"""
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 加载标准化规则
            if 'normalization_rules' in config:
                self.normalization_rules = config['normalization_rules']
                
                # 构建别名映射
                for entity_type, rules in self.normalization_rules.items():
                    if 'aliases' in rules:
                        for alias, canonical in rules['aliases'].items():
                            self.alias_map[alias.lower()] = {
                                'canonical': canonical,
                                'type': entity_type
                            }
            
            logger.info(f"Loaded {len(self.alias_map)} normalization rules from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def normalize(self, entity: Entity) -> Entity:
        """
        标准化实体
        
        Args:
            entity: 待标准化实体
            
        Returns:
            Entity: 标准化后的实体
        """
        text_lower = entity.text.lower()
        
        # 查找别名映射
        if text_lower in self.alias_map:
            mapping = self.alias_map[text_lower]
            entity.normalized = mapping['canonical']
            entity.metadata['original_text'] = entity.text
            entity.metadata['normalization_rule'] = 'alias_mapping'
        
        # 如果没有找到别名映射，使用原文本作为标准化结果
        if not entity.normalized:
            entity.normalized = entity.text
        
        return entity
    
    def normalize_batch(self, entities: List[Entity]) -> List[Entity]:
        """批量标准化实体"""
        return [self.normalize(e) for e in entities]


class CustomEntityRecognizer:
    """
    自定义实体识别器
    
    使用规则匹配补充 spaCy 的识别能力
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化自定义识别器"""
        self.config_path = config_path
        self.patterns = {}
        self.entity_examples = {}
        
        if config_path:
            self.load_config(config_path)
        
        # 编译内置模式
        self._compile_patterns()
    
    def load_config(self, config_path: str):
        """加载配置文件中的示例和模式"""
        try:
            path = Path(config_path)
            if not path.exists():
                return
            
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 加载实体类型示例
            if 'entity_types' in config:
                for entity_def in config['entity_types']:
                    label = entity_def['name']
                    self.entity_examples[label] = entity_def.get('examples', [])
            
            logger.info(f"Loaded {len(self.entity_examples)} entity type examples")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def _compile_patterns(self):
        """编译识别模式"""
        # 政府机构模式
        self.patterns['GOV_ORG'] = [
            re.compile(r'(国务院|发改委|财政部|央行|证监会|银保监会|外交部|国防部|教育部|科技部|工信部|公安部|民政部|司法部|人社部|自然资源部|生态环境部|住建部|交通部|水利部|农业农村部|商务部|文旅部|卫健委|退役军人部|应急部|人民银行|审计署)'),
            re.compile(r'(美联储|财政部|国务院|白宫|国会|参议院|众议院|最高法院|联邦法院)'),
            re.compile(r'(\w+省\w+局|\w+市\w+委|\w+区\w+办)'),
        ]
        
        # 政策/法规模式
        self.patterns['LAW_POLICY'] = [
            re.compile(r'((?:十四五|十三五|十二五).{0,10}规划)'),
            re.compile(r'((?:新|旧).{0,5}版.{0,10}条例)'),
            re.compile(r'((?:中华人民共和国|中国).{0,10}法)'),
            re.compile(r'(碳中和.{0,10}政策|碳达峰.{0,10}方案)'),
            re.compile(r'(外商投资.{0,10}法|数据安全.{0,10}法|个人信息保护.{0,10}法)'),
        ]
        
        # 事件模式
        self.patterns['EVENT'] = [
            re.compile(r'(两会|党代会|人大会议|政协会议)'),
            re.compile(r'(达沃斯.{0,10}论坛|博鳌.{0,10}论坛)'),
            re.compile(r'(奥运会|亚运会|世界杯)'),
            re.compile(r'((?:中美|中欧|中日).{0,10}贸易.{0,10}战)'),
            re.compile(r'((?:第\d+届).{0,10}会议)'),
        ]
    
    def recognize(self, text: str) -> List[Entity]:
        """
        使用规则识别实体
        
        Args:
            text: 输入文本
            
        Returns:
            List[Entity]: 识别的实体列表
        """
        entities = []
        
        for label, patterns in self.patterns.items():
            label_name = self._get_label_name(label)
            
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entity = Entity(
                        text=match.group(0),
                        label=label,
                        label_name=label_name,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.85,  # 规则匹配的置信度
                        source='rule'
                    )
                    entities.append(entity)
        
        # 检查示例匹配 (简单精确匹配)
        for label, examples in self.entity_examples.items():
            label_name = self._get_label_name(label)
            for example in examples:
                if len(example) > 2:  # 避免太短的匹配
                    for match in re.finditer(re.escape(example), text):
                        # 检查是否已被识别
                        already_found = any(
                            e.start <= match.start() < e.end or e.start < match.end() <= e.end
                            for e in entities
                        )
                        if not already_found:
                            entity = Entity(
                                text=example,
                                label=label,
                                label_name=label_name,
                                start=match.start(),
                                end=match.end(),
                                confidence=0.75,  # 示例匹配的置信度
                                source='custom'
                            )
                            entities.append(entity)
        
        return entities
    
    def _get_label_name(self, label: str) -> str:
        """获取标签的中文名称"""
        label_map = {
            'GPE': '国家/地区',
            'GOV_ORG': '政府机构',
            'ORG': '公司/组织',
            'PERSON': '人物',
            'EVENT': '事件',
            'LAW_POLICY': '政策/法规'
        }
        return label_map.get(label, label)


class EntityRecognizer:
    """
    实体识别器
    
    整合 spaCy 和自定义规则的完整实体识别系统
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        language: str = 'zh',
        use_spacy: bool = True
    ):
        """
        初始化实体识别器
        
        Args:
            config_path: entities.yaml 路径
            language: 主要语言 ('zh', 'en')
            use_spacy: 是否使用 spaCy
        """
        self.config_path = config_path
        self.language = language
        self.use_spacy = use_spacy and SPACY_AVAILABLE
        
        # 加载配置
        self.normalizer = EntityNormalizer(config_path)
        self.custom_recognizer = CustomEntityRecognizer(config_path)
        
        # 加载 spaCy 模型
        self.nlp = None
        if self.use_spacy:
            self._load_spacy_model(language)
        
        # 实体标签映射
        self.label_map = {
            'GPE': '国家/地区',
            'GOV_ORG': '政府机构',
            'ORG': '公司/组织',
            'PERSON': '人物',
            'EVENT': '事件',
            'LAW_POLICY': '政策/法规'
        }
    
    def _load_spacy_model(self, language: str):
        """加载 spaCy 模型"""
        try:
            if language == 'zh':
                # 尝试加载中文模型
                model_names = ['zh_core_web_sm', 'zh_core_web_md', 'zh_core_web_lg']
                for model_name in model_names:
                    try:
                        self.nlp = spacy.load(model_name)
                        logger.info(f"Loaded spaCy model: {model_name}")
                        break
                    except OSError:
                        continue
                
                if not self.nlp:
                    logger.warning("Chinese spaCy model not found. Install with: python -m spacy download zh_core_web_sm")
                    self.use_spacy = False
            
            elif language == 'en':
                # 尝试加载英文模型
                try:
                    self.nlp = spacy.load('en_core_web_sm')
                    logger.info("Loaded spaCy model: en_core_web_sm")
                except OSError:
                    logger.warning("English spaCy model not found. Install with: python -m spacy download en_core_web_sm")
                    self.use_spacy = False
        
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            self.use_spacy = False
    
    def _map_spacy_label(self, spacy_label: str) -> Tuple[str, str]:
        """
        映射 spaCy 标签到自定义标签
        
        Returns:
            Tuple[str, str]: (label, label_name)
        """
        # spaCy 标准标签到自定义标签的映射
        mapping = {
            'GPE': ('GPE', '国家/地区'),
            'LOC': ('GPE', '国家/地区'),
            'ORG': ('ORG', '公司/组织'),
            'PERSON': ('PERSON', '人物'),
            'EVENT': ('EVENT', '事件'),
            'LAW': ('LAW_POLICY', '政策/法规'),
            'PRODUCT': ('ORG', '公司/组织'),
            'WORK_OF_ART': ('EVENT', '事件'),
        }
        
        return mapping.get(spacy_label, ('ORG', '公司/组织'))
    
    def recognize(self, text: str) -> EntityRecognitionResult:
        """
        识别文本中的实体
        
        Args:
            text: 输入文本
            
        Returns:
            EntityRecognitionResult: 识别结果
        """
        import time
        start_time = time.time()
        
        all_entities = []
        
        # 1. 使用 spaCy 识别
        if self.use_spacy and self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                label, label_name = self._map_spacy_label(ent.label_)
                entity = Entity(
                    text=ent.text,
                    label=label,
                    label_name=label_name,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.9,  # spaCy 置信度
                    source='spacy'
                )
                all_entities.append(entity)
        
        # 2. 使用自定义规则识别
        custom_entities = self.custom_recognizer.recognize(text)
        all_entities.extend(custom_entities)
        
        # 3. 合并重叠实体 (保留置信度高的)
        all_entities = self._merge_overlapping_entities(all_entities)
        
        # 4. 标准化实体
        all_entities = self.normalizer.normalize_batch(all_entities)
        
        # 5. 统计
        entity_counts = {}
        for entity in all_entities:
            entity_counts[entity.label] = entity_counts.get(entity.label, 0) + 1
        
        processing_time = (time.time() - start_time) * 1000
        
        return EntityRecognitionResult(
            original_text=text,
            entities=all_entities,
            entity_counts=entity_counts,
            processing_time_ms=processing_time
        )
    
    def _merge_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        合并重叠的实体，保留置信度高的
        
        Args:
            entities: 实体列表
            
        Returns:
            List[Entity]: 合并后的实体列表
        """
        if not entities:
            return entities
        
        # 按起始位置和置信度排序
        sorted_entities = sorted(entities, key=lambda e: (e.start, -e.confidence))
        
        merged = []
        for entity in sorted_entities:
            # 检查是否与已有实体重叠
            overlap = False
            for existing in merged:
                if (entity.start < existing.end and entity.end > existing.start):
                    # 有重叠
                    overlap = True
                    if entity.confidence > existing.confidence:
                        # 当前实体置信度更高，替换
                        merged.remove(existing)
                        merged.append(entity)
                        break
            
            if not overlap:
                merged.append(entity)
        
        return merged
    
    def recognize_batch(self, texts: List[str]) -> List[EntityRecognitionResult]:
        """批量识别实体"""
        return [self.recognize(text) for text in texts]
    
    def extract_entities_by_type(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> List[Entity]:
        """
        按类型提取实体
        
        Args:
            text: 输入文本
            entity_types: 指定实体类型列表
            
        Returns:
            List[Entity]: 指定类型的实体
        """
        result = self.recognize(text)
        
        if entity_types:
            return [e for e in result.entities if e.label in entity_types]
        
        return result.entities
    
    def get_entity_summary(self, text: str) -> Dict[str, Any]:
        """
        获取实体摘要
        
        Args:
            text: 输入文本
            
        Returns:
            Dict: 实体摘要
        """
        result = self.recognize(text)
        
        # 按类型分组
        by_type = {}
        for entity in result.entities:
            if entity.label not in by_type:
                by_type[entity.label] = []
            by_type[entity.label].append({
                'text': entity.text,
                'normalized': entity.normalized,
                'confidence': entity.confidence
            })
        
        return {
            'total_entities': len(result.entities),
            'by_type': by_type,
            'counts': result.entity_counts,
            'processing_time_ms': result.processing_time_ms
        }


# 便捷函数
def create_recognizer(
    config_path: Optional[str] = None,
    language: str = 'zh'
) -> EntityRecognizer:
    """创建实体识别器"""
    return EntityRecognizer(config_path, language)


def recognize_entities(text: str, config_path: Optional[str] = None) -> List[Entity]:
    """快速识别实体"""
    recognizer = create_recognizer(config_path)
    result = recognizer.recognize(text)
    return result.entities


def extract_entities(text: str, entity_types: List[str], config_path: Optional[str] = None) -> List[Entity]:
    """按类型提取实体"""
    recognizer = create_recognizer(config_path)
    return recognizer.extract_entities_by_type(text, entity_types)


# 示例用法
if __name__ == '__main__':
    # 示例文本
    sample_text = """
    中国国务院总理李克强在两会期间宣布，十四五规划将重点关注科技创新。
    阿里巴巴和腾讯等科技公司表示支持。美联储主席鲍威尔也表示，美国将加强与中国的技术合作。
    根据外商投资法，外资企业可以享受更多优惠政策。
    """
    
    # 创建识别器
    recognizer = create_recognizer(
        config_path='entities.yaml',
        language='zh'
    )
    
    # 识别实体
    print("=== 实体识别示例 ===\n")
    result = recognizer.recognize(sample_text)
    
    print(f"原文：{sample_text}\n")
    print(f"识别到 {len(result.entities)} 个实体:\n")
    
    for entity in result.entities:
        print(f"  - {entity.text} ({entity.label_name})")
        if entity.normalized and entity.normalized != entity.text:
            print(f"    标准化：{entity.normalized}")
        print(f"    置信度：{entity.confidence}, 来源：{entity.source}")
    
    print(f"\n处理时间：{result.processing_time_ms:.2f}ms")
    print(f"\n实体统计：{result.entity_counts}")
    
    # 获取摘要
    print("\n=== 实体摘要 ===")
    summary = recognizer.get_entity_summary(sample_text)
    for label, entities in summary['by_type'].items():
        print(f"\n{label}:")
        for e in entities:
            print(f"  - {e['text']} -> {e['normalized']}")
