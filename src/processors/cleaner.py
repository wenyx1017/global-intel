#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据清洗管道 (Data Cleaning Pipeline)
=====================================
用于全球情报系统的文本数据预处理和清洗模块

功能:
- 文本规范化
- 噪声去除
- 编码统一
- 格式标准化
- 重复检测
"""

import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class CleaningResult:
    """清洗结果数据类"""
    original_text: str
    cleaned_text: str
    changes_made: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'original_text': self.original_text,
            'cleaned_text': self.cleaned_text,
            'changes_made': self.changes_made,
            'quality_score': self.quality_score,
            'timestamp': self.timestamp.isoformat()
        }


class TextCleaner:
    """
    文本清洗器
    
    提供多层次的文本清洗功能，从基础清理到高级规范化
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化清洗器
        
        Args:
            config: 配置字典，可包含:
                - remove_html: bool, 是否移除 HTML 标签
                - normalize_whitespace: bool, 是否规范化空白字符
                - remove_special_chars: bool, 是否移除特殊字符
                - normalize_punctuation: bool, 是否规范化标点
                - min_text_length: int, 最小文本长度
                - language: str, 主要语言 ('zh', 'en', 'auto')
        """
        self.config = config or {}
        self.remove_html = self.config.get('remove_html', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.remove_special_chars = self.config.get('remove_special_chars', False)
        self.normalize_punctuation = self.config.get('normalize_punctuation', True)
        self.min_text_length = self.config.get('min_text_length', 10)
        self.language = self.config.get('language', 'auto')
        
        # 编译常用正则表达式
        self._compile_patterns()
    
    def _compile_patterns(self):
        """编译正则表达式模式"""
        # HTML 标签
        self.html_pattern = re.compile(r'<[^>]+>')
        # URL
        self.url_pattern = re.compile(
            r'https?://[^\s<>\"{}|\\^`\[\]]+'
        )
        # 多余空白
        self.whitespace_pattern = re.compile(r'\s+')
        # 特殊字符 (保留中文、英文、数字、基本标点)
        self.special_char_pattern = re.compile(
            r'[^\w\s\u4e00-\u9fff,.!?;:()""''""''-]'
        )
        # 连续标点
        self.repeated_punct_pattern = re.compile(r'([!?.]){2,}')
        # 全角半角标点映射
        self.fullwidth_punct = {
            '，': ',', '。': '.', '！': '!', '？': '?',
            '；': ';', '：': ':', '（': '(', '）': ')',
            '【': '[', '】': ']', '「': '"', '」': '"',
            '『': '"', '』': '"', '、': ',', '·': '.'
        }
    
    def clean(self, text: str, options: Optional[Dict[str, bool]] = None) -> CleaningResult:
        """
        执行完整清洗流程
        
        Args:
            text: 原始文本
            options: 临时选项覆盖
            
        Returns:
            CleaningResult: 清洗结果
        """
        if not text or not isinstance(text, str):
            return CleaningResult(
                original_text=text or '',
                cleaned_text='',
                changes_made=['empty_or_invalid_input'],
                quality_score=0.0
            )
        
        original = text
        changes = []
        
        # 1. 移除 HTML 标签
        if self.remove_html and (options is None or options.get('remove_html', True)):
            text = self._remove_html(text)
            if text != original:
                changes.append('removed_html_tags')
        
        # 2. 移除或保留 URL
        text = self._handle_urls(text)
        
        # 3. 规范化空白字符
        if self.normalize_whitespace:
            text = self._normalize_whitespace(text)
            if text != original:
                changes.append('normalized_whitespace')
        
        # 4. 规范化标点符号
        if self.normalize_punctuation:
            text = self._normalize_punctuation(text)
            if text != original:
                changes.append('normalized_punctuation')
        
        # 5. 移除特殊字符 (可选)
        if self.remove_special_chars:
            text = self._remove_special_chars(text)
            if text != original:
                changes.append('removed_special_chars')
        
        # 6. 去除首尾空白
        text = text.strip()
        
        # 7. 计算质量分数
        quality_score = self._calculate_quality_score(text)
        
        # 8. 检查最小长度
        if len(text) < self.min_text_length:
            changes.append(f'below_min_length({len(text)}<{self.min_text_length})')
        
        return CleaningResult(
            original_text=original,
            cleaned_text=text,
            changes_made=changes,
            quality_score=quality_score
        )
    
    def _remove_html(self, text: str) -> str:
        """移除 HTML 标签"""
        return self.html_pattern.sub('', text)
    
    def _handle_urls(self, text: str) -> str:
        """
        处理 URL
        默认保留 URL，但可以进行规范化
        """
        # 这里可以选择移除或保留 URL
        # 当前实现：保留 URL
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """规范化空白字符"""
        # 将各种空白字符替换为单个空格
        text = self.whitespace_pattern.sub(' ', text)
        # 移除中文和英文之间的多余空格
        text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)
        return text
    
    def _normalize_punctuation(self, text: str) -> str:
        """规范化标点符号"""
        # 全角转半角标点
        for full, half in self.fullwidth_punct.items():
            text = text.replace(full, half)
        
        # 移除连续重复的标点
        text = self.repeated_punct_pattern.sub(r'\1', text)
        
        return text
    
    def _remove_special_chars(self, text: str) -> str:
        """移除特殊字符"""
        return self.special_char_pattern.sub('', text)
    
    def _calculate_quality_score(self, text: str) -> float:
        """
        计算文本质量分数 (0-1)
        
        考虑因素:
        - 文本长度
        - 中英文比例
        - 标点密度
        - 特殊字符比例
        """
        if not text:
            return 0.0
        
        score = 1.0
        
        # 长度评分
        length = len(text)
        if length < 10:
            score *= 0.5
        elif length < 50:
            score *= 0.7
        elif length > 5000:
            score *= 0.8
        
        # 中文字符比例 (对于中文文本应该是高的)
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if self.language == 'zh' and length > 0:
            chinese_ratio = chinese_chars / length
            if chinese_ratio < 0.3:
                score *= 0.8
        
        # 标点密度
        punct_count = len(re.findall(r'[,.!?;:()""''""''-]', text))
        punct_density = punct_count / max(length, 1)
        if punct_density > 0.3:  # 标点过多
            score *= 0.9
        
        return round(score, 2)
    
    def clean_batch(self, texts: List[str]) -> List[CleaningResult]:
        """批量清洗文本"""
        return [self.clean(text) for text in texts]


class Deduplicator:
    """
    去重处理器
    
    基于多种策略检测和移除重复内容
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化去重器
        
        Args:
            config: 配置字典，可包含:
                - strategy: str, 去重策略 ('exact', 'normalized', 'fuzzy', 'hash')
                - case_insensitive: bool, 是否忽略大小写
                - ignore_punctuation: bool, 是否忽略标点
                - similarity_threshold: float, 模糊匹配阈值 (0-1)
        """
        self.config = config or {}
        self.strategy = self.config.get('strategy', 'normalized')
        self.case_insensitive = self.config.get('case_insensitive', True)
        self.ignore_punctuation = self.config.get('ignore_punctuation', True)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.85)
        
        self._seen_hashes = set()
        self._seen_normalized = set()
    
    def _normalize_for_dedup(self, text: str) -> str:
        """为去重规范化文本"""
        normalized = text
        
        # 忽略大小写
        if self.case_insensitive:
            normalized = normalized.lower()
        
        # 忽略标点
        if self.ignore_punctuation:
            normalized = re.sub(r'[^\w\s\u4e00-\u9fff]', '', normalized)
        
        # 移除多余空白
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
    
    def _calculate_hash(self, text: str) -> str:
        """计算文本哈希"""
        normalized = self._normalize_for_dedup(text)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        使用简单的字符级重叠系数
        """
        if not text1 or not text2:
            return 0.0
        
        set1 = set(text1)
        set2 = set(text2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def is_duplicate(self, text: str) -> Tuple[bool, str]:
        """
        检查文本是否重复
        
        Args:
            text: 待检查文本
            
        Returns:
            Tuple[bool, str]: (是否重复, 重复原因)
        """
        normalized = self._normalize_for_dedup(text)
        text_hash = self._calculate_hash(text)
        
        # 精确哈希匹配
        if text_hash in self._seen_hashes:
            return True, 'exact_hash_match'
        
        # 规范化文本匹配
        if normalized in self._seen_normalized:
            return True, 'normalized_match'
        
        # 模糊匹配 (如果需要)
        if self.strategy == 'fuzzy':
            for seen in self._seen_normalized:
                similarity = self._calculate_similarity(normalized, seen)
                if similarity >= self.similarity_threshold:
                    return True, f'fuzzy_match({similarity:.2f})'
        
        # 记录新的文本
        self._seen_hashes.add(text_hash)
        self._seen_normalized.add(normalized)
        
        return False, 'unique'
    
    def deduplicate(self, texts: List[str]) -> Dict[str, Any]:
        """
        对文本列表去重
        
        Args:
            texts: 文本列表
            
        Returns:
            Dict: 包含去重结果
        """
        unique_texts = []
        duplicates = []
        stats = {
            'total': len(texts),
            'unique': 0,
            'duplicates': 0,
            'duplicate_rate': 0.0
        }
        
        for text in texts:
            is_dup, reason = self.is_duplicate(text)
            if is_dup:
                duplicates.append({
                    'text': text,
                    'reason': reason
                })
            else:
                unique_texts.append(text)
        
        stats['unique'] = len(unique_texts)
        stats['duplicates'] = len(duplicates)
        stats['duplicate_rate'] = len(duplicates) / max(len(texts), 1)
        
        return {
            'unique_texts': unique_texts,
            'duplicates': duplicates,
            'stats': stats
        }
    
    def reset(self):
        """重置去重状态"""
        self._seen_hashes.clear()
        self._seen_normalized.clear()


class DataCleaningPipeline:
    """
    数据清洗管道
    
    组合多个清洗步骤，提供完整的清洗流程
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化清洗管道
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.cleaner = TextCleaner(self.config.get('cleaner', {}))
        self.deduplicator = Deduplicator(self.config.get('deduplicator', {}))
        self.steps = []
    
    def add_step(self, name: str, func, **kwargs):
        """添加自定义清洗步骤"""
        self.steps.append({
            'name': name,
            'func': func,
            'kwargs': kwargs
        })
    
    def process(self, text: str) -> Dict[str, Any]:
        """
        处理单条文本
        
        Args:
            text: 原始文本
            
        Returns:
            Dict: 处理结果
        """
        # 基础清洗
        clean_result = self.cleaner.clean(text)
        
        # 检查重复
        is_duplicate, dup_reason = self.deduplicator.is_duplicate(clean_result.cleaned_text)
        
        # 执行自定义步骤
        custom_results = {}
        processed_text = clean_result.cleaned_text
        for step in self.steps:
            try:
                result = step['func'](processed_text, **step['kwargs'])
                custom_results[step['name']] = result
                if isinstance(result, str):
                    processed_text = result
            except Exception as e:
                logger.warning(f"Step {step['name']} failed: {e}")
        
        return {
            'original': text,
            'cleaned': clean_result.cleaned_text,
            'final': processed_text,
            'is_duplicate': is_duplicate,
            'duplicate_reason': dup_reason,
            'quality_score': clean_result.quality_score,
            'changes': clean_result.changes_made,
            'custom_results': custom_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def process_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        批量处理文本
        
        Args:
            texts: 文本列表
            
        Returns:
            Dict: 批量处理结果
        """
        results = []
        for text in texts:
            result = self.process(text)
            results.append(result)
        
        # 汇总统计
        total = len(results)
        duplicates = sum(1 for r in results if r['is_duplicate'])
        avg_quality = sum(r['quality_score'] for r in results) / max(total, 1)
        
        return {
            'results': results,
            'summary': {
                'total_processed': total,
                'duplicates_found': duplicates,
                'unique_count': total - duplicates,
                'duplicate_rate': duplicates / max(total, 1),
                'average_quality_score': round(avg_quality, 2)
            }
        }


# 便捷函数
def create_pipeline(config: Optional[Dict[str, Any]] = None) -> DataCleaningPipeline:
    """创建数据清洗管道"""
    return DataCleaningPipeline(config)


def clean_text(text: str, config: Optional[Dict[str, Any]] = None) -> str:
    """快速清洗文本"""
    pipeline = create_pipeline(config)
    result = pipeline.process(text)
    return result['final']


def deduplicate_texts(texts: List[str], config: Optional[Dict[str, Any]] = None) -> List[str]:
    """快速去重文本列表"""
    pipeline = create_pipeline(config)
    result = pipeline.process_batch(texts)
    return [r['final'] for r in result['results'] if not r['is_duplicate']]


# 示例用法
if __name__ == '__main__':
    # 示例文本
    sample_texts = [
        "<p>中国国务院今天发布了新的政策。</p>",
        "  美联储 宣布 加息   25 个基点  ",
        "阿里巴巴集团发布财报",
        "阿里巴巴集团发布财报",  # 重复
        "腾讯发布新游戏",
    ]
    
    # 创建管道
    pipeline = create_pipeline({
        'cleaner': {
            'remove_html': True,
            'normalize_whitespace': True,
            'normalize_punctuation': True
        },
        'deduplicator': {
            'strategy': 'normalized',
            'case_insensitive': True
        }
    })
    
    # 处理
    print("=== 数据清洗管道示例 ===\n")
    for text in sample_texts:
        result = pipeline.process(text)
        print(f"原始：{text}")
        print(f"清洗后：{result['final']}")
        print(f"重复：{result['is_duplicate']} ({result['duplicate_reason']})")
        print(f"质量分：{result['quality_score']}")
        print()
    
    # 批量处理
    print("=== 批量处理统计 ===")
    batch_result = pipeline.process_batch(sample_texts)
    print(f"总数：{batch_result['summary']['total_processed']}")
    print(f"去重后：{batch_result['summary']['unique_count']}")
    print(f"重复率：{batch_result['summary']['duplicate_rate']:.2%}")
