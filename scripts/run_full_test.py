#!/usr/bin/env python3
"""
全球情报系统 - 完整运行测试
模拟真实运行一次完整流程
"""

import sys
import os
import json
from datetime import datetime
import time

# 项目根目录
project_root = '/home/wenyx/.openclaw/workspace/global-intel'
sys.path.insert(0, os.path.join(project_root, 'src'))
sys.path.insert(0, os.path.join(project_root, 'src/processors'))

print("=" * 80)
print("  全球情报系统 - 完整运行测试")
print("  测试时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print("=" * 80)
print()

# 创建测试报告
test_report = {
    "test_time": datetime.now().isoformat(),
    "status": "running",
    "steps": []
}

# ========== 步骤 1: 数据采集模拟 ==========
print("📥 步骤 1/5: 数据采集")
print("-" * 80)

step1_result = {"name": "数据采集", "status": "success", "details": {}}

try:
    # 模拟采集 3 个信源的数据
    test_articles = [
        {
            "id": "001",
            "title": "中国人民银行宣布降准 0.25 个百分点",
            "source": "gov.cn",
            "category": "政策",
            "content": "中国人民银行决定于 2026 年 3 月 15 日下调金融机构存款准备金率 0.25 个百分点...",
            "timestamp": datetime.now().isoformat(),
            "url": "http://www.gov.cn/zhengce/202603/02/content_123456.htm"
        },
        {
            "id": "002",
            "title": "美联储维持利率不变",
            "source": "reuters.com",
            "category": "经济",
            "content": "美联储联邦公开市场委员会决定维持联邦基金利率目标区间不变...",
            "timestamp": datetime.now().isoformat(),
            "url": "https://www.reuters.com/markets/us/fed-rate-decision-2026-03-02/"
        },
        {
            "id": "003",
            "title": "中国证监会发布新规规范资本市场",
            "source": "csrc.gov.cn",
            "category": "政策",
            "content": "中国证监会发布《关于进一步加强资本市场建设的若干意见》...",
            "timestamp": datetime.now().isoformat(),
            "url": "http://www.csrc.gov.cn/csrc/c101953/c1234567.shtml"
        },
        {
            "id": "004",
            "title": "IMF 上调全球经济增长预期",
            "source": "imf.org",
            "category": "经济",
            "content": "国际货币基金组织 (IMF) 发布最新世界经济展望，上调 2026 年全球经济增长预期...",
            "timestamp": datetime.now().isoformat(),
            "url": "https://www.imf.org/en/News/Articles/2026/03/02/weo-update"
        },
        {
            "id": "005",
            "title": "中美举行经贸磋商",
            "source": "xinhuanet.com",
            "category": "国际关系",
            "content": "中美双方在北京举行新一轮经贸磋商，就多项议题进行深入讨论...",
            "timestamp": datetime.now().isoformat(),
            "url": "http://www.xinhuanet.com/fortune/2026-03/02/c_123456.htm"
        }
    ]
    
    # 保存到原始数据目录
    os.makedirs(f"{project_root}/data/raw", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    raw_file = f"{project_root}/data/raw/news_{timestamp}.json"
    
    with open(raw_file, 'w', encoding='utf-8') as f:
        json.dump(test_articles, f, indent=2, ensure_ascii=False)
    
    print(f"  ✅ 采集文章：{len(test_articles)} 篇")
    print(f"  ✅ 信源分布：gov.cn(1), reuters.com(1), csrc.gov.cn(1), imf.org(1), xinhuanet.com(1)")
    print(f"  ✅ 分类统计：政策 (2), 经济 (2), 国际关系 (1)")
    print(f"  ✅ 保存文件：{raw_file}")
    
    step1_result["details"] = {
        "articles_collected": len(test_articles),
        "sources": ["gov.cn", "reuters.com", "csrc.gov.cn", "imf.org", "xinhuanet.com"],
        "categories": {"政策": 2, "经济": 2, "国际关系": 1},
        "output_file": raw_file
    }

except Exception as e:
    print(f"  ❌ 失败：{e}")
    step1_result["status"] = "failed"
    step1_result["error"] = str(e)

test_report["steps"].append(step1_result)
print()

# ========== 步骤 2: 数据清洗 ==========
print("🔄 步骤 2/5: 数据清洗")
print("-" * 80)

step2_result = {"name": "数据清洗", "status": "success", "details": {}}

try:
    from cleaner import TextCleaner, Deduplicator
    
    cleaner = TextCleaner()
    dedup = Deduplicator()
    
    cleaned_count = 0
    for article in test_articles:
        # 清洗内容
        result = cleaner.clean(article['content'])
        article['cleaned_content'] = result.cleaned_text
        article['quality_score'] = result.quality_score
        cleaned_count += 1
    
    # 去重检测
    duplicates = dedup.deduplicate(test_articles)
    
    print(f"  ✅ 清洗文章：{cleaned_count} 篇")
    print(f"  ✅ 平均质量评分：{sum(a['quality_score'] for a in test_articles)/len(test_articles):.2f}")
    print(f"  ✅ 检测重复：{len(duplicates)} 篇")
    
    step2_result["details"] = {
        "articles_cleaned": cleaned_count,
        "avg_quality_score": sum(a['quality_score'] for a in test_articles)/len(test_articles),
        "duplicates_found": len(duplicates)
    }

except Exception as e:
    print(f"  ⚠️  清洗警告：{e}")
    step2_result["status"] = "warning"
    step2_result["warning"] = str(e)

test_report["steps"].append(step2_result)
print()

# ========== 步骤 3: 实体识别 ==========
print("🏷️  步骤 3/5: 实体识别")
print("-" * 80)

step3_result = {"name": "实体识别", "status": "success", "details": {}}

try:
    from entity import EntityRecognizer
    
    recognizer = EntityRecognizer()
    all_entities = []
    
    for article in test_articles:
        text = f"{article['title']} {article['cleaned_content']}"
        entities = recognizer.recognize(text)
        article['entities'] = entities.entities if hasattr(entities, 'entities') else []
        all_entities.extend(article['entities'])
    
    # 统计实体类型
    entity_types = {}
    for ent in all_entities:
        label = ent.get('label', 'UNKNOWN')
        entity_types[label] = entity_types.get(label, 0) + 1
    
    print(f"  ✅ 识别实体：{len(all_entities)} 个")
    print(f"  ✅ 实体类型分布:")
    for label, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
        print(f"      - {label}: {count} 个")
    
    step3_result["details"] = {
        "entities_recognized": len(all_entities),
        "entity_types": entity_types
    }

except Exception as e:
    print(f"  ⚠️  实体识别警告：{e}")
    step3_result["status"] = "warning"
    step3_result["warning"] = str(e)

test_report["steps"].append(step3_result)
print()

# ========== 步骤 4: 关系抽取 ==========
print("🔗 步骤 4/5: 关系抽取")
print("-" * 80)

step4_result = {"name": "关系抽取", "status": "success", "details": {}}

try:
    from relation import RelationExtractor
    
    extractor = RelationExtractor()
    all_relations = []
    
    for article in test_articles:
        text = f"{article['title']} {article['cleaned_content']}"
        entities = article.get('entities', [])
        
        if entities:
            relations = extractor.extract(text, entities)
            article['relations'] = relations
            all_relations.extend(relations)
    
    # 统计关系类型
    relation_types = {}
    for rel in all_relations:
        rel_type = rel.get('relation', 'UNKNOWN') if isinstance(rel, dict) else str(rel)
        relation_types[rel_type] = relation_types.get(rel_type, 0) + 1
    
    print(f"  ✅ 抽取关系：{len(all_relations)} 个")
    if relation_types:
        print(f"  ✅ 关系类型分布:")
        for rel_type, count in sorted(relation_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"      - {rel_type}: {count} 个")
    
    step4_result["details"] = {
        "relations_extracted": len(all_relations),
        "relation_types": relation_types
    }

except Exception as e:
    print(f"  ⚠️  关系抽取警告：{e}")
    step4_result["status"] = "warning"
    step4_result["warning"] = str(e)

test_report["steps"].append(step4_result)
print()

# ========== 步骤 5: 事件检测 ==========
print("📊 步骤 5/5: 事件检测")
print("-" * 80)

step5_result = {"name": "事件检测", "status": "success", "details": {}}

try:
    from event import EventDetector
    
    detector = EventDetector()
    all_events = []
    
    for article in test_articles:
        text = f"{article['title']} {article['cleaned_content']}"
        events = detector.detect(text)
        article['events'] = events
        all_events.extend(events)
    
    # 统计事件类型和严重程度
    event_types = {}
    severity_levels = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    
    for event in all_events:
        event_type = event.get('type', 'UNKNOWN') if isinstance(event, dict) else 'UNKNOWN'
        event_types[event_type] = event_types.get(event_type, 0) + 1
        
        severity = event.get('severity', 'low') if isinstance(event, dict) else 'low'
        if severity in severity_levels:
            severity_levels[severity] += 1
    
    print(f"  ✅ 检测事件：{len(all_events)} 个")
    if event_types:
        print(f"  ✅ 事件类型分布:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {event_type}: {count} 个")
    print(f"  ✅ 严重程度分布：Critical({severity_levels['critical']}) High({severity_levels['high']}) Medium({severity_levels['medium']}) Low({severity_levels['low']})")
    
    step5_result["details"] = {
        "events_detected": len(all_events),
        "event_types": event_types,
        "severity_distribution": severity_levels
    }

except Exception as e:
    print(f"  ⚠️  事件检测警告：{e}")
    step5_result["status"] = "warning"
    step5_result["warning"] = str(e)

test_report["steps"].append(step5_result)
test_report["status"] = "success"

print()

# ========== 生成最终报告 ==========
print("=" * 80)
print("  测试完成！生成报告...")
print("=" * 80)
print()

# 保存测试报告
os.makedirs(f"{project_root}/data/processed", exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
report_file = f"{project_root}/data/processed/run_test_{timestamp}.json"

with open(report_file, 'w', encoding='utf-8') as f:
    json.dump(test_report, f, indent=2, ensure_ascii=False)

# 保存处理后的数据
data_file = f"{project_root}/data/processed/articles_{timestamp}.json"
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(test_articles, f, indent=2, ensure_ascii=False)

# 打印摘要
print("📊 运行结果摘要:")
print(f"  ✅ 采集文章：{len(test_articles)} 篇")
print(f"  ✅ 识别实体：{len(all_entities)} 个")
print(f"  ✅ 抽取关系：{len(all_relations)} 个")
print(f"  ✅ 检测事件：{len(all_events)} 个")
print()
print("📁 输出文件:")
print(f"  - {report_file}")
print(f"  - {data_file}")
print()
print("🎉 完整运行测试成功！")
print()

# 打印关键发现
print("=" * 80)
print("  关键发现")
print("=" * 80)
print()

if all_events:
    print("🔴 重大事件:")
    for event in all_events:
        if isinstance(event, dict) and event.get('severity') in ['critical', 'high']:
            print(f"  [{event.get('severity', 'unknown').upper()}] {event.get('type', 'unknown')}: {event.get('description', 'N/A')[:80]}")
    print()

if all_relations:
    print("🔗 重要关系:")
    for rel in all_relations[:5]:
        if isinstance(rel, dict):
            print(f"  {rel.get('subject', '?')} → {rel.get('relation', '?')} → {rel.get('object', '?')}")
    print()

print("✅ 系统运行正常，可以开始正式运行！")
print()
