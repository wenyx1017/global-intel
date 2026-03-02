#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信源评分算法模块 (Source Scoring Module)

实现信源评价的四个维度：
- 准确性 (30%)：与其他信源交叉验证
- 真实性 (25%)：检查域名、作者、引用
- 客观性 (25%)：情感分析，偏见检测
- 重大性 (20%)：被引用次数、传播范围
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import re


@dataclass
class SourceScore:
    """信源评分数据结构"""
    source_id: str
    accuracy: float  # 准确性 (0-100)
    authenticity: float  # 真实性 (0-100)
    objectivity: float  # 客观性 (0-100)
    importance: float  # 重大性 (0-100)
    total_score: float  # 总分 (0-100)
    grade: str  # 等级 (S/A/B/C)
    evaluated_at: datetime
    
    # 权重配置
    WEIGHT_ACCURACY = 0.30
    WEIGHT_AUTHENTICITY = 0.25
    WEIGHT_OBJECTIVITY = 0.25
    WEIGHT_IMPORTANCE = 0.20
    
    def __post_init__(self):
        """计算总分和等级"""
        if self.total_score is None:
            self.total_score = (
                self.accuracy * self.WEIGHT_ACCURACY +
                self.authenticity * self.WEIGHT_AUTHENTICITY +
                self.objectivity * self.WEIGHT_OBJECTIVITY +
                self.importance * self.WEIGHT_IMPORTANCE
            )
        if self.grade is None:
            self.grade = self._calculate_grade()
    
    def _calculate_grade(self) -> str:
        """根据总分计算等级"""
        if self.total_score >= 90:
            return "S"
        elif self.total_score >= 80:
            return "A"
        elif self.total_score >= 70:
            return "B"
        else:
            return "C"
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "source_id": self.source_id,
            "accuracy": round(self.accuracy, 2),
            "authenticity": round(self.authenticity, 2),
            "objectivity": round(self.objectivity, 2),
            "importance": round(self.importance, 2),
            "total_score": round(self.total_score, 2),
            "grade": self.grade,
            "evaluated_at": self.evaluated_at.isoformat()
        }


class SourceScorer:
    """信源评分器"""
    
    # 可信域名列表（第一手信源）
    TRUSTED_DOMAINS = {
        # 政府/官方
        "gov.cn", "gov.uk", "gov.us", "whitehouse.gov",
        # 国际组织
        "imf.org", "worldbank.org", "un.org", "iec.ch",
        # 金融监管
        "sec.gov", "csrc.gov.cn", "pbc.gov.cn",
        # 能源
        "iea.org", "eia.gov", "nea.gov.cn",
        # 科技
        "arxiv.org", "nature.com", "science.org", "most.gov.cn",
        # 权威媒体
        "reuters.com", "bloomberg.com", "xinhuanet.com",
    }
    
    # 需要谨慎的域名
    SUSPICIOUS_TLDS = {".xyz", ".top", ".club", ".work", ".date"}
    
    def __init__(self):
        self.cross_validation_cache: Dict[str, List[Dict]] = {}
    
    def calculate_accuracy(self, articles: List[Dict], 
                          other_sources: List[Dict]) -> float:
        """
        计算准确性分数（交叉验证）
        
        Args:
            articles: 当前信源的文章列表
            other_sources: 其他信源的文章列表用于交叉验证
            
        Returns:
            准确性分数 (0-100)
        """
        if not articles:
            return 50.0  # 默认中等分数
        
        # 如果没有其他信源用于交叉验证，基于信源本身质量评分
        if not other_sources:
            return self._accuracy_from_source_quality(articles)
        
        # 提取当前信源的关键事实
        current_facts = self._extract_facts(articles)
        
        # 与其他信源交叉验证
        verified_count = 0
        total_claims = len(current_facts)
        
        for fact in current_facts:
            if self._verify_fact(fact, other_sources):
                verified_count += 1
        
        # 基础准确率
        base_accuracy = (verified_count / total_claims * 100) if total_claims > 0 else 50
        
        # 考虑事实的时效性（越新的事实权重越高）
        recency_bonus = self._calculate_recency_bonus(articles)
        
        return min(100, base_accuracy + recency_bonus)
    
    def _accuracy_from_source_quality(self, articles: List[Dict]) -> float:
        """
        当没有其他信源时，基于文章质量评估准确性
        
        Args:
            articles: 文章列表
            
        Returns:
            准确性分数 (0-100)
        """
        if not articles:
            return 50.0
        
        quality_score = 0
        
        for article in articles:
            content = article.get("content", "") + " " + article.get("title", "")
            
            # 1. 有具体数据支撑（数字、百分比等）
            has_data = bool(re.search(r'\d+(?:\.\d+)?%?', content))
            if has_data:
                quality_score += 20
            
            # 2. 有引用来源
            has_citation = bool(re.search(r'据 | 来源|according to|citing', content, re.IGNORECASE))
            if has_citation:
                quality_score += 20
            
            # 3. 文章长度适中（不是标题党）
            if len(content) > 200:
                quality_score += 20
            
            # 4. 没有极端词汇
            extreme_words = ["绝对", "肯定", "100%", "最"]
            has_extreme = any(word in content for word in extreme_words)
            if not has_extreme:
                quality_score += 20
            
            # 5. 有明确的发布时间
            if article.get("published_at"):
                quality_score += 20
        
        return min(100, quality_score / len(articles))
    
    def calculate_authenticity(self, source_info: Dict) -> float:
        """
        计算真实性分数（域名/作者/引用验证）
        
        Args:
            source_info: 信源信息 {domain, author, citations, established_date, ...}
            
        Returns:
            真实性分数 (0-100)
        """
        score = 0.0
        
        # 1. 域名验证 (40 分)
        domain_score = self._verify_domain(source_info.get("domain", ""))
        score += domain_score * 0.4
        
        # 2. 作者验证 (30 分)
        author_score = self._verify_author(source_info.get("author", ""))
        score += author_score * 0.3
        
        # 3. 引用验证 (20 分)
        citation_score = self._verify_citations(source_info.get("citations", 0))
        score += citation_score * 0.2
        
        # 4. 成立时间 (10 分)
        age_score = self._verify_source_age(source_info.get("established_date"))
        score += age_score * 0.1
        
        return score
    
    def calculate_objectivity(self, articles: List[Dict]) -> float:
        """
        计算客观性分数（情感分析/偏见检测）
        
        Args:
            articles: 文章列表
            
        Returns:
            客观性分数 (0-100)
        """
        if not articles:
            return 50.0  # 默认中等分数
        
        sentiment_scores = []
        bias_scores = []
        
        for article in articles:
            content = article.get("content", "") + " " + article.get("title", "")
            
            # 情感分析
            sentiment = self._analyze_sentiment(content)
            sentiment_scores.append(sentiment)
            
            # 偏见检测
            bias = self._detect_bias(content)
            bias_scores.append(bias)
        
        # 情感中立度（越接近 0 越中立）
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        neutrality_score = max(0, 100 - abs(avg_sentiment) * 100)
        
        # 偏见分数（越低越客观）
        avg_bias = sum(bias_scores) / len(bias_scores)
        objectivity_score = max(0, 100 - avg_bias * 100)
        
        # 综合得分
        return (neutrality_score + objectivity_score) / 2
    
    def calculate_importance(self, articles: List[Dict]) -> float:
        """
        计算重大性分数（传播度/引用次数）
        
        Args:
            articles: 文章列表
            
        Returns:
            重大性分数 (0-100)
        """
        if not articles:
            return 0.0
        
        total_impact = 0
        
        for article in articles:
            # 引用次数
            citations = article.get("citations", 0)
            
            # 传播范围（阅读量、分享数等）
            views = article.get("views", 0)
            shares = article.get("shares", 0)
            
            # 计算单篇文章影响力
            article_impact = (
                min(100, citations * 10) * 0.4 +
                min(100, views / 1000) * 0.3 +
                min(100, shares / 100) * 0.3
            )
            
            total_impact += article_impact
        
        # 平均影响力
        avg_impact = total_impact / len(articles)
        
        # 时效性加成（最近的文章权重更高）
        recency_multiplier = self._calculate_recency_multiplier(articles)
        
        return min(100, avg_impact * recency_multiplier)
    
    def evaluate(self, source_id: str, source_info: Dict, 
                articles: List[Dict], other_sources: List[Dict]) -> SourceScore:
        """
        完整评价信源
        
        Args:
            source_id: 信源 ID
            source_info: 信源基本信息
            articles: 文章列表
            other_sources: 其他信源用于交叉验证
            
        Returns:
            SourceScore 评分结果
        """
        accuracy = self.calculate_accuracy(articles, other_sources)
        authenticity = self.calculate_authenticity(source_info)
        objectivity = self.calculate_objectivity(articles)
        importance = self.calculate_importance(articles)
        
        return SourceScore(
            source_id=source_id,
            accuracy=accuracy,
            authenticity=authenticity,
            objectivity=objectivity,
            importance=importance,
            total_score=None,  # 自动计算
            grade=None,  # 自动计算
            evaluated_at=datetime.now()
        )
    
    # ========== 内部辅助方法 ==========
    
    def _extract_facts(self, articles: List[Dict]) -> List[Dict]:
        """从文章中提取可验证的事实"""
        facts = []
        for article in articles:
            content = article.get("content", "")
            # 简单的事实提取：数字、日期、专有名词等
            # 实际实现可以使用 NLP 技术
            numbers = re.findall(r'\d+(?:\.\d+)?(?:%|亿元|万人)?', content)
            dates = re.findall(r'\d{4}年\d{1,2}月\d{1,2}日', content)
            
            facts.append({
                "article_id": article.get("id"),
                "numbers": numbers,
                "dates": dates,
                "headline": article.get("title", "")
            })
        return facts
    
    def _verify_fact(self, fact: Dict, other_sources: List[Dict]) -> bool:
        """验证事实是否与其他信源一致"""
        # 简单实现：检查数字是否在其他信源中出现
        for source in other_sources:
            for article in source.get("articles", []):
                content = article.get("content", "")
                # 检查关键数字是否匹配
                for num in fact.get("numbers", []):
                    if num in content:
                        return True
        return False
    
    def _calculate_recency_bonus(self, articles: List[Dict]) -> float:
        """计算时效性加分"""
        if not articles:
            return 0
        
        now = datetime.now()
        total_bonus = 0
        
        for article in articles:
            pub_date = article.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date)
                    except:
                        continue
                
                days_old = (now - pub_date).days
                if days_old <= 1:
                    total_bonus += 5
                elif days_old <= 7:
                    total_bonus += 2
        
        return min(10, total_bonus / len(articles))
    
    def _verify_domain(self, domain: str) -> float:
        """验证域名可信度"""
        if not domain:
            return 0
        
        domain = domain.lower()
        
        # 可信域名直接满分
        for trusted in self.TRUSTED_DOMAINS:
            if trusted in domain:
                return 100
        
        # 可疑域名后缀扣分
        for suspicious in self.SUSPICIOUS_TLDS:
            if domain.endswith(suspicious):
                return 30
        
        # 政府/教育域名加分
        if domain.endswith(".gov") or domain.endswith(".edu"):
            return 90
        
        # 常见媒体域名
        if domain.endswith(".com") or domain.endswith(".org"):
            return 70
        
        return 50
    
    def _verify_author(self, author: str) -> float:
        """验证作者可信度"""
        if not author:
            return 30  # 匿名作者中等偏下分数
        
        # 知名机构作者
        known_authors = ["新华社", "Reuters", "Bloomberg", "央视", "人民日报"]
        if any(known in author for known in known_authors):
            return 100
        
        # 有具体署名的作者
        if len(author) > 2:
            return 70
        
        return 50
    
    def _verify_citations(self, citations: int) -> float:
        """验证引用次数"""
        if citations >= 100:
            return 100
        elif citations >= 50:
            return 90
        elif citations >= 20:
            return 80
        elif citations >= 10:
            return 70
        elif citations >= 5:
            return 60
        elif citations >= 1:
            return 50
        return 30
    
    def _verify_source_age(self, established_date) -> float:
        """验证信源成立时间"""
        if not established_date:
            return 50
        
        try:
            if isinstance(established_date, str):
                established = datetime.fromisoformat(established_date)
            else:
                established = established_date
            
            years_old = (datetime.now() - established).days / 365
            
            if years_old >= 10:
                return 100
            elif years_old >= 5:
                return 90
            elif years_old >= 2:
                return 80
            elif years_old >= 1:
                return 70
            else:
                return 60
        except:
            return 50
    
    def _analyze_sentiment(self, text: str) -> float:
        """
        情感分析（简化版）
        返回 -1 到 1，0 表示中立
        """
        # 正面词汇
        positive_words = ["增长", "成功", "突破", "利好", "上涨", "积极", "优秀"]
        # 负面词汇
        negative_words = ["下跌", "失败", "风险", "危机", "衰退", "负面", "警告"]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        total = positive_count + negative_count
        if total == 0:
            return 0
        
        # 返回 -1 到 1
        return (positive_count - negative_count) / total
    
    def _detect_bias(self, text: str) -> float:
        """
        偏见检测（简化版）
        返回 0 到 1，0 表示无偏见
        """
        # 极端词汇
        extreme_words = ["绝对", "肯定", "必然", "无疑", "100%", "最"]
        # 主观词汇
        subjective_words = ["我认为", "我觉得", "显然", "明显", "毫无疑问"]
        
        extreme_count = sum(1 for word in extreme_words if word in text)
        subjective_count = sum(1 for word in subjective_words if word in text)
        
        # 计算偏见分数（0-1）
        bias_score = (extreme_count + subjective_count) / len(text.split()) * 10
        return min(1, bias_score)
    
    def _calculate_recency_multiplier(self, articles: List[Dict]) -> float:
        """计算时效性乘数"""
        if not articles:
            return 1.0
        
        now = datetime.now()
        recent_count = 0
        
        for article in articles:
            pub_date = article.get("published_at")
            if pub_date:
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date)
                    except:
                        continue
                
                days_old = (now - pub_date).days
                if days_old <= 3:
                    recent_count += 1
        
        # 如果有超过一半的文章是最近的，给予 1.2 倍加成
        if recent_count > len(articles) / 2:
            return 1.2
        
        return 1.0


# 便捷函数
def grade_source(source_id: str, source_info: Dict, articles: List[Dict], 
                other_sources: List[Dict]) -> Dict:
    """
    便捷函数：评价信源并返回字典格式结果
    
    Args:
        source_id: 信源 ID
        source_info: 信源信息
        articles: 文章列表
        other_sources: 其他信源用于交叉验证
        
    Returns:
        评分结果字典
    """
    scorer = SourceScorer()
    score = scorer.evaluate(source_id, source_info, articles, other_sources)
    return score.to_dict()


if __name__ == "__main__":
    # 测试示例
    test_source = {
        "domain": "reuters.com",
        "author": "Reuters Staff",
        "citations": 150,
        "established_date": "1851-01-01"
    }
    
    test_articles = [
        {
            "id": "1",
            "title": "Global Markets Rise",
            "content": "Stock markets increased by 2.5% today...",
            "published_at": datetime.now(),
            "citations": 50,
            "views": 10000,
            "shares": 500
        }
    ]
    
    scorer = SourceScorer()
    result = scorer.evaluate("test_source", test_source, test_articles, [])
    
    print(f"信源评分结果: {result.to_dict()}")
