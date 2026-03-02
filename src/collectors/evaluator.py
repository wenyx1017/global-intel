#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信源评价器 (Source Evaluator)

信源评价体系主模块，实现：
1. 信源评价流程管理
2. 自动评分与分级
3. 优胜劣汰机制
4. 评价结果存储与查询
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import asdict

from scoring import SourceScorer, SourceScore


class SourceDatabase:
    """信源评价结果数据库"""
    
    def __init__(self, db_path: str = "source_evaluations.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 评价结果表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                accuracy REAL,
                authenticity REAL,
                objectivity REAL,
                importance REAL,
                total_score REAL,
                grade TEXT,
                evaluated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 信源信息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id TEXT PRIMARY KEY,
                domain TEXT,
                author TEXT,
                established_date TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 评价历史表（用于趋势分析）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                total_score REAL,
                grade TEXT,
                evaluated_at TIMESTAMP,
                FOREIGN KEY (source_id) REFERENCES sources(source_id)
            )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_id ON evaluations(source_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_grade ON evaluations(grade)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluated_at ON evaluations(evaluated_at)")
        
        conn.commit()
        conn.close()
    
    def save_evaluation(self, score: SourceScore):
        """保存评价结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 插入评价结果
        cursor.execute("""
            INSERT INTO evaluations 
            (source_id, accuracy, authenticity, objectivity, importance, 
             total_score, grade, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            score.source_id,
            score.accuracy,
            score.authenticity,
            score.objectivity,
            score.importance,
            score.total_score,
            score.grade,
            score.evaluated_at.isoformat()  # 转换为字符串
        ))
        
        # 插入评价历史
        cursor.execute("""
            INSERT INTO evaluation_history 
            (source_id, total_score, grade, evaluated_at)
            VALUES (?, ?, ?, ?)
        """, (
            score.source_id,
            score.total_score,
            score.grade,
            score.evaluated_at.isoformat()  # 转换为字符串
        ))
        
        conn.commit()
        conn.close()
    
    def get_latest_evaluation(self, source_id: str) -> Optional[Dict]:
        """获取最新评价结果"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_id, accuracy, authenticity, objectivity, importance,
                   total_score, grade, evaluated_at
            FROM evaluations
            WHERE source_id = ?
            ORDER BY evaluated_at DESC
            LIMIT 1
        """, (source_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "source_id": row[0],
                "accuracy": row[1],
                "authenticity": row[2],
                "objectivity": row[3],
                "importance": row[4],
                "total_score": row[5],
                "grade": row[6],
                "evaluated_at": row[7]
            }
        return None
    
    def get_all_evaluations(self, min_score: float = 0) -> List[Dict]:
        """获取所有评价结果（可过滤最低分）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.source_id, e.accuracy, e.authenticity, e.objectivity,
                   e.importance, e.total_score, e.grade, e.evaluated_at,
                   s.domain, s.status
            FROM evaluations e
            LEFT JOIN sources s ON e.source_id = s.source_id
            WHERE e.total_score >= ?
            ORDER BY e.total_score DESC
        """, (min_score,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "source_id": row[0],
                "accuracy": row[1],
                "authenticity": row[2],
                "objectivity": row[3],
                "importance": row[4],
                "total_score": row[5],
                "grade": row[6],
                "evaluated_at": row[7],
                "domain": row[8],
                "status": row[9]
            })
        
        conn.close()
        return results
    
    def get_sources_by_grade(self, grade: str) -> List[Dict]:
        """按等级获取信源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.source_id, e.total_score, e.grade, e.evaluated_at,
                   s.domain, s.status
            FROM evaluations e
            LEFT JOIN sources s ON e.source_id = s.source_id
            WHERE e.grade = ?
            ORDER BY e.total_score DESC
        """, (grade,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "source_id": row[0],
                "total_score": row[1],
                "grade": row[2],
                "evaluated_at": row[3],
                "domain": row[4],
                "status": row[5]
            })
        
        conn.close()
        return results
    
    def register_source(self, source_id: str, source_info: Dict):
        """注册新信源"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sources 
            (source_id, domain, author, established_date, status, updated_at)
            VALUES (?, ?, ?, ?, 'active', CURRENT_TIMESTAMP)
        """, (
            source_id,
            source_info.get("domain", ""),
            source_info.get("author", ""),
            source_info.get("established_date")
        ))
        
        conn.commit()
        conn.close()
    
    def update_source_status(self, source_id: str, status: str):
        """更新信源状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE sources 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE source_id = ?
        """, (status, source_id))
        
        conn.commit()
        conn.close()
    
    def get_evaluation_trend(self, source_id: str, days: int = 30) -> List[Dict]:
        """获取信源评价趋势"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        cursor.execute("""
            SELECT total_score, grade, evaluated_at
            FROM evaluation_history
            WHERE source_id = ? AND evaluated_at >= ?
            ORDER BY evaluated_at ASC
        """, (source_id, cutoff_date.isoformat()))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "total_score": row[0],
                "grade": row[1],
                "evaluated_at": row[2]
            })
        
        conn.close()
        return results


class SourceEvaluator:
    """信源评价器主类"""
    
    def __init__(self, db_path: str = "source_evaluations.db"):
        self.scorer = SourceScorer()
        self.db = SourceDatabase(db_path)
        self.evaluation_cache: Dict[str, SourceScore] = {}
    
    def evaluate_source(self, source_id: str, source_info: Dict, 
                       articles: List[Dict], other_sources: List[Dict]) -> SourceScore:
        """
        评价单个信源
        
        Args:
            source_id: 信源 ID
            source_info: 信源基本信息
            articles: 文章列表
            other_sources: 其他信源用于交叉验证
            
        Returns:
            SourceScore 评分结果
        """
        # 注册信源
        self.db.register_source(source_id, source_info)
        
        # 执行评价
        score = self.scorer.evaluate(source_id, source_info, articles, other_sources)
        
        # 保存结果
        self.db.save_evaluation(score)
        
        # 更新缓存
        self.evaluation_cache[source_id] = score
        
        # 检查是否需要淘汰
        self._check_elimination(source_id, score)
        
        return score
    
    def evaluate_all_sources(self, sources_data: List[Dict]) -> List[SourceScore]:
        """
        批量评价所有信源
        
        Args:
            sources_data: 信源数据列表
                [{
                    "source_id": "...",
                    "source_info": {...},
                    "articles": [...]
                }]
            
        Returns:
            评分结果列表
        """
        results = []
        
        for i, source_data in enumerate(sources_data):
            source_id = source_data["source_id"]
            source_info = source_data["source_info"]
            articles = source_data["articles"]
            
            # 其他信源用于交叉验证（排除自己）- 只传递 articles
            other_sources = [
                {"articles": s["articles"]} for j, s in enumerate(sources_data) 
                if j != i
            ]
            
            score = self.evaluate_source(
                source_id, source_info, articles, other_sources
            )
            results.append(score)
        
        return results
    
    def get_source_grade(self, source_id: str) -> Optional[str]:
        """获取信源等级"""
        eval_result = self.db.get_latest_evaluation(source_id)
        return eval_result["grade"] if eval_result else None
    
    def get_sources_by_grade(self, grade: str) -> List[Dict]:
        """获取指定等级的所有信源"""
        return self.db.get_sources_by_grade(grade)
    
    def get_elimination_candidates(self) -> List[Dict]:
        """获取待淘汰信源（C 级）"""
        return self.db.get_sources_by_grade("C")
    
    def _check_elimination(self, source_id: str, score: SourceScore):
        """检查是否需要淘汰信源"""
        if score.grade == "C":
            # C 级信源标记为待淘汰
            self.db.update_source_status(source_id, "pending_elimination")
            
            # 检查历史评价，如果连续 3 次都是 C 级，则淘汰
            trend = self.db.get_evaluation_trend(source_id, days=90)
            c_count = sum(1 for t in trend if t["grade"] == "C")
            
            if c_count >= 3:
                self.db.update_source_status(source_id, "eliminated")
    
    def promote_source(self, source_id: str):
        """提升信源等级（手动干预）"""
        if source_id in self.evaluation_cache:
            score = self.evaluation_cache[source_id]
            # 提升总分 5 分
            new_score = SourceScore(
                source_id=score.source_id,
                accuracy=min(100, score.accuracy + 5),
                authenticity=min(100, score.authenticity + 5),
                objectivity=min(100, score.objectivity + 5),
                importance=min(100, score.importance + 5),
                total_score=None,
                grade=None,
                evaluated_at=datetime.now()
            )
            self.db.save_evaluation(new_score)
            self.evaluation_cache[source_id] = new_score
    
    def generate_report(self) -> Dict:
        """生成评价报告"""
        all_evals = self.db.get_all_evaluations()
        
        # 统计各等级数量
        grade_counts = {"S": 0, "A": 0, "B": 0, "C": 0}
        for eval_data in all_evals:
            grade = eval_data.get("grade", "C")
            if grade in grade_counts:
                grade_counts[grade] += 1
        
        # 计算平均分
        avg_scores = {}
        if all_evals:
            avg_scores = {
                "accuracy": sum(e["accuracy"] for e in all_evals) / len(all_evals),
                "authenticity": sum(e["authenticity"] for e in all_evals) / len(all_evals),
                "objectivity": sum(e["objectivity"] for e in all_evals) / len(all_evals),
                "importance": sum(e["importance"] for e in all_evals) / len(all_evals),
                "total": sum(e["total_score"] for e in all_evals) / len(all_evals)
            }
        
        return {
            "generated_at": datetime.now().isoformat(),
            "total_sources": len(all_evals),
            "grade_distribution": grade_counts,
            "average_scores": avg_scores,
            "top_sources": all_evals[:10],  # 前 10 名
            "elimination_candidates": self.get_elimination_candidates()
        }


# 便捷函数
def quick_evaluate(sources_data: List[Dict], db_path: str = "source_evaluations.db") -> List[Dict]:
    """
    快速评价信源并返回结果列表
    
    Args:
        sources_data: 信源数据列表
        db_path: 数据库路径
        
    Returns:
        评分结果字典列表
    """
    evaluator = SourceEvaluator(db_path)
    scores = evaluator.evaluate_all_sources(sources_data)
    return [score.to_dict() for score in scores]


if __name__ == "__main__":
    # 测试示例
    test_sources = [
        {
            "source_id": "reuters",
            "source_info": {
                "domain": "reuters.com",
                "author": "Reuters Staff",
                "citations": 1000,
                "established_date": "1851-01-01"
            },
            "articles": [
                {
                    "id": "1",
                    "title": "Market Update: Stock markets rise 2.5%",
                    "content": "Stock markets increased by 2.5% today. According to market data, the S&P 500 gained 2.5% in trading. Analysts cite positive economic data as the reason for the 2.5% increase.",
                    "published_at": datetime.now(),
                    "citations": 100,
                    "views": 50000,
                    "shares": 1000
                }
            ]
        },
        {
            "source_id": "bloomberg",
            "source_info": {
                "domain": "bloomberg.com",
                "author": "Bloomberg News",
                "citations": 800,
                "established_date": "1981-01-01"
            },
            "articles": [
                {
                    "id": "1",
                    "title": "Stock markets gain 2.5% on economic data",
                    "content": "Major indices rose 2.5% today following positive economic reports. The 2.5% gain marks a strong performance across sectors.",
                    "published_at": datetime.now(),
                    "citations": 80,
                    "views": 40000,
                    "shares": 800
                }
            ]
        },
        {
            "source_id": "unknown_blog",
            "source_info": {
                "domain": "random-blog.xyz",
                "author": "Anonymous",
                "citations": 5,
                "established_date": None
            },
            "articles": [
                {
                    "id": "1",
                    "title": "My Opinion: This is absolutely the best!",
                    "content": "I think this is absolutely the best investment ever. I feel like everyone should buy now. This is clearly the obvious choice.",
                    "published_at": datetime.now(),
                    "citations": 1,
                    "views": 100,
                    "shares": 5
                }
            ]
        }
    ]
    
    # 执行评价
    results = quick_evaluate(test_sources)
    
    print("\n=== 信源评价报告 ===\n")
    for result in results:
        print(f"信源：{result['source_id']}")
        print(f"  等级：{result['grade']}")
        print(f"  总分：{result['total_score']}")
        print(f"  准确性：{result['accuracy']}")
        print(f"  真实性：{result['authenticity']}")
        print(f"  客观性：{result['objectivity']}")
        print(f"  重大性：{result['importance']}")
        print()
    
    # 生成报告
    evaluator = SourceEvaluator()
    report = evaluator.generate_report()
    print("\n=== 总体统计 ===")
    print(f"总信源数：{report['total_sources']}")
    print(f"等级分布：{report['grade_distribution']}")
    print(f"平均分数：{report['average_scores']}")
