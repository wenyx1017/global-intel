"""
关系抽取模块
Relation Extraction Module for Global Intelligence System

从文本中抽取实体之间的关系，支持多种关系类型。
"""

import re
import yaml
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Relation:
    """关系数据类"""
    head: str  # 头实体
    tail: str  # 尾实体
    relation_type: str  # 关系类型
    label: str  # 关系标签
    confidence: float  # 置信度
    context: str  # 上下文
    head_type: str = ""  # 头实体类型
    tail_type: str = ""  # 尾实体类型
    subtype: Optional[str] = None  # 子类型（用于合作/对抗）


@dataclass
class RelationPattern:
    """关系抽取模式"""
    pattern: str
    regex: Optional[re.Pattern] = None
    keywords: List[str] = field(default_factory=list)


class RelationExtractor:
    """关系抽取器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化关系抽取器
        
        Args:
            config_path: 配置文件路径，默认为 relations.yaml
        """
        if config_path is None:
            config_path = Path(__file__).parent / "relations.yaml"
        
        self.config_path = Path(config_path)
        self.relation_types = []
        self.extraction_rules = {}
        self.confidence_config = {}
        
        self._load_config()
        self._compile_patterns()
    
    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.relation_types = config.get('relation_types', [])
        self.extraction_rules = config.get('extraction_rules', {})
        self.confidence_config = config.get('confidence', {})
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        for rule_name, rules in self.extraction_rules.items():
            if 'patterns' in rules:
                for i, pattern in enumerate(rules['patterns']):
                    # 将 {head} 和 {tail} 转换为正则表达式
                    regex_pattern = pattern.replace('{head}', r'(.+?)').replace('{tail}', r'(.+?)')
                    rules['patterns'][i] = {
                        'original': pattern,
                        'regex': re.compile(regex_pattern)
                    }
    
    def extract(self, text: str, entities: Optional[List[Dict]] = None) -> List[Relation]:
        """
        从文本中抽取关系
        
        Args:
            text: 输入文本
            entities: 已识别的实体列表（可选）
            
        Returns:
            抽取的关系列表
        """
        relations = []
        
        # 遍历所有关系类型
        for rel_type in self.relation_types:
            rel_name = rel_type['name']
            rel_label = rel_type['label']
            
            # 获取该关系类型的抽取规则
            rules = self.extraction_rules.get(rel_name, {})
            
            # 模式匹配
            pattern_relations = self._extract_by_patterns(text, rel_name, rel_label, rules)
            relations.extend(pattern_relations)
            
            # 关键词匹配
            keyword_relations = self._extract_by_keywords(text, rel_name, rel_label, rules, entities)
            relations.extend(keyword_relations)
        
        # 去重和排序
        relations = self._deduplicate(relations)
        relations.sort(key=lambda r: r.confidence, reverse=True)
        
        return relations
    
    def _extract_by_patterns(self, text: str, rel_name: str, rel_label: str, 
                             rules: Dict) -> List[Relation]:
        """通过模式匹配抽取关系"""
        relations = []
        patterns = rules.get('patterns', [])
        
        for pattern_info in patterns:
            if isinstance(pattern_info, dict) and 'regex' in pattern_info:
                regex = pattern_info['regex']
                matches = regex.findall(text)
                
                for match in matches:
                    if len(match) >= 2:
                        head, tail = match[0].strip(), match[1].strip()
                        
                        # 计算置信度
                        confidence = self.confidence_config.get('pattern_match', 0.8)
                        
                        relation = Relation(
                            head=head,
                            tail=tail,
                            relation_type=rel_name,
                            label=rel_label,
                            confidence=confidence,
                            context=text
                        )
                        relations.append(relation)
        
        return relations
    
    def _extract_by_keywords(self, text: str, rel_name: str, rel_label: str,
                            rules: Dict, entities: Optional[List[Dict]] = None) -> List[Relation]:
        """通过关键词抽取关系"""
        relations = []
        keywords = rules.get('keywords', [])
        
        if not keywords:
            return relations
        
        # 查找关键词位置
        for keyword in keywords:
            if keyword in text:
                # 如果有实体信息，尝试关联实体
                if entities:
                    entity_relations = self._link_entities(text, keyword, rel_name, 
                                                          rel_label, entities)
                    relations.extend(entity_relations)
                else:
                    # 没有实体信息时，使用简单的上下文抽取
                    context_relations = self._extract_from_context(text, keyword, 
                                                                   rel_name, rel_label)
                    relations.extend(context_relations)
        
        return relations
    
    def _link_entities(self, text: str, keyword: str, rel_name: str, 
                      rel_label: str, entities: List[Dict]) -> List[Relation]:
        """将关键词与实体关联"""
        relations = []
        
        # 获取关系类型的 domain 和 range
        rel_type_config = next((r for r in self.relation_types if r['name'] == rel_name), None)
        if not rel_type_config:
            return relations
        
        domain_types = rel_type_config.get('domain', [])
        range_types = rel_type_config.get('range', [])
        
        # 简单的实体配对逻辑
        for i, entity1 in enumerate(entities):
            if entity1.get('type') in domain_types:
                for entity2 in entities[i+1:]:
                    if entity2.get('type') in range_types:
                        # 检查实体是否在关键词附近
                        if self._entities_near_keyword(text, entity1, entity2, keyword):
                            confidence = self.confidence_config.get('keyword_match', 0.6)
                            
                            relation = Relation(
                                head=entity1.get('text', ''),
                                tail=entity2.get('text', ''),
                                relation_type=rel_name,
                                label=rel_label,
                                confidence=confidence,
                                context=text,
                                head_type=entity1.get('type', ''),
                                tail_type=entity2.get('type', '')
                            )
                            relations.append(relation)
        
        return relations
    
    def _entities_near_keyword(self, text: str, entity1: Dict, entity2: Dict, 
                               keyword: str) -> bool:
        """检查两个实体是否在关键词附近"""
        keyword_pos = text.find(keyword)
        if keyword_pos == -1:
            return False
        
        entity1_pos = text.find(entity1.get('text', ''))
        entity2_pos = text.find(entity2.get('text', ''))
        
        if entity1_pos == -1 or entity2_pos == -1:
            return False
        
        # 检查实体是否在关键词的合理距离内（100 字符）
        window = 100
        return (abs(entity1_pos - keyword_pos) < window and 
                abs(entity2_pos - keyword_pos) < window)
    
    def _extract_from_context(self, text: str, keyword: str, 
                             rel_name: str, rel_label: str) -> List[Relation]:
        """从上下文简单抽取关系"""
        relations = []
        
        # 简单的句子分割
        sentences = re.split(r'[。！？.!?]', text)
        
        for sentence in sentences:
            if keyword in sentence and len(sentence.strip()) > 5:
                # 提取关键词前后的名词短语（简化处理）
                parts = sentence.split(keyword)
                if len(parts) >= 2:
                    head = parts[0].strip()[-10:] if len(parts[0]) > 10 else parts[0].strip()
                    tail = parts[1].strip()[:10] if len(parts[1]) > 10 else parts[1].strip()
                    
                    if head and tail:
                        confidence = self.confidence_config.get('keyword_match', 0.6)
                        
                        relation = Relation(
                            head=head,
                            tail=tail,
                            relation_type=rel_name,
                            label=rel_label,
                            confidence=confidence,
                            context=sentence
                        )
                        relations.append(relation)
        
        return relations
    
    def _deduplicate(self, relations: List[Relation]) -> List[Relation]:
        """去重关系"""
        seen = set()
        unique_relations = []
        
        for rel in relations:
            # 创建去重键
            key = (rel.head, rel.tail, rel.relation_type)
            
            if key not in seen:
                seen.add(key)
                unique_relations.append(rel)
            else:
                # 如果已存在，保留置信度更高的
                existing = next((r for r in unique_relations 
                               if (r.head, r.tail, r.relation_type) == key), None)
                if existing and rel.confidence > existing.confidence:
                    existing.confidence = rel.confidence
        
        return unique_relations
    
    def filter_by_confidence(self, relations: List[Relation], 
                            threshold: Optional[float] = None) -> List[Relation]:
        """
        根据置信度过滤关系
        
        Args:
            relations: 关系列表
            threshold: 置信度阈值，默认为配置中的 min_threshold
            
        Returns:
            过滤后的关系列表
        """
        if threshold is None:
            threshold = self.confidence_config.get('min_threshold', 0.5)
        
        return [r for r in relations if r.confidence >= threshold]
    
    def get_relation_types(self) -> List[str]:
        """获取所有关系类型"""
        return [rt['name'] for rt in self.relation_types]
    
    def get_relation_labels(self) -> Dict[str, str]:
        """获取关系类型到标签的映射"""
        return {rt['name']: rt['label'] for rt in self.relation_types}


def extract_relations(text: str, entities: Optional[List[Dict]] = None,
                     config_path: Optional[str] = None) -> List[Relation]:
    """
    便捷函数：从文本中抽取关系
    
    Args:
        text: 输入文本
        entities: 已识别的实体列表（可选）
        config_path: 配置文件路径（可选）
        
    Returns:
        抽取的关系列表
    """
    extractor = RelationExtractor(config_path)
    return extractor.extract(text, entities)


# 使用示例
if __name__ == "__main__":
    # 示例文本
    text = "国务院发布十四五规划，该规划将影响能源行业。阿里巴巴 CEO 张三表示，公司总部位于杭州。"
    
    # 示例实体
    entities = [
        {"text": "国务院", "type": "GOV_ORG"},
        {"text": "十四五规划", "type": "LAW_POLICY"},
        {"text": "能源行业", "type": "ORG"},
        {"text": "阿里巴巴", "type": "ORG"},
        {"text": "张三", "type": "PERSON"},
        {"text": "杭州", "type": "GPE"},
    ]
    
    # 抽取关系
    extractor = RelationExtractor()
    relations = extractor.extract(text, entities)
    
    # 过滤低置信度关系
    high_conf_relations = extractor.filter_by_confidence(relations, threshold=0.6)
    
    print(f"抽取到 {len(relations)} 个关系")
    print(f"高置信度关系 {len(high_conf_relations)} 个")
    print("\n关系详情:")
    for rel in high_conf_relations:
        print(f"  {rel.head} --[{rel.label}]--> {rel.tail} (置信度：{rel.confidence})")
