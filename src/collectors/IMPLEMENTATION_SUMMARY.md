# 信源评价系统实现总结

## 完成情况 ✓

### 1. 核心文件

| 文件 | 说明 | 行数 |
|------|------|------|
| `scoring.py` | 评分算法模块 | ~500 行 |
| `evaluator.py` | 评价器主模块 | ~450 行 |
| `evaluator.go` | Go 语言接口 | ~250 行 |
| `README_EVALUATOR.md` | 使用说明 | ~200 行 |

### 2. 评价维度实现

#### 准确性 (30%) ✓
- **交叉验证**：提取文章中的数字、日期等关键事实，与其他信源比对
- **质量评分**：无其他信源时，基于数据支撑、引用来源、文章长度等评分
- **时效性加分**：新发布的事实权重更高

#### 真实性 (25%) ✓
- **域名验证**：可信域名（gov.cn、reuters.com 等）满分，可疑 TLD 扣分
- **作者验证**：知名机构（新华社、Reuters 等）满分，匿名作者低分
- **引用验证**：根据引用次数评分
- **成立时间**：信源历史越久越可信

#### 客观性 (25%) ✓
- **情感分析**：检测正面/负面词汇比例，越中立即分数越高
- **偏见检测**：识别极端词汇（"绝对"、"100%"）和主观表达（"我认为"）

#### 重大性 (20%) ✓
- **引用次数** (40%)：被其他文章引用次数
- **传播范围** (60%)：阅读量、分享数
- **时效性加成**：近期内容权重更高

### 3. 信源分级 ✓

| 等级 | 分数 | 处理策略 |
|------|------|----------|
| **S 级** | 90-100 | 优先采用，高频更新 |
| **A 级** | 80-89 | 正常采用，标准更新 |
| **B 级** | 70-79 | 谨慎采用，降低频率 |
| **C 级** | <70 | 淘汰，移除信源 |

### 4. 自动淘汰机制 ✓
- C 级信源自动标记为 `pending_elimination`
- 连续 3 次 C 级自动标记为 `eliminated`
- 支持手动干预（`promote_source`）

### 5. 数据存储 ✓
- SQLite 数据库存储评价结果
- 三张表：`evaluations`（最新结果）、`evaluation_history`（历史趋势）、`sources`（信源信息）
- 支持查询、统计、趋势分析

### 6. Go 语言集成 ✓
- 提供 Go 接口调用 Python 评价器
- 支持单个/批量评价
- 支持查询等级、生成报告

## 测试结果

### 测试信源
- **reuters.com** (S 级，93.92 分) - 权威媒体
- **bloomberg.com** (S 级，93.06 分) - 权威媒体
- **gov.cn** (A 级，85.25 分) - 政府网站
- **xinhuanet.com** (B 级，79.69 分) - 官方媒体
- **random-blog.xyz** (C 级，39.97 分) - 未知博客

### 评分分布
```
S 级：2 个 (40%)
A 级：1 个 (20%)
B 级：1 个 (20%)
C 级：1 个 (20%)
平均总分：78.38
```

## 使用示例

### Python
```python
from evaluator import quick_evaluate

results = quick_evaluate(sources_data)
for r in results:
    print(f"{r['source_id']}: {r['grade']} ({r['total_score']})")
```

### Go
```go
evaluator := NewSourceEvaluator("python3", "./collectors", "source_evaluations.db")
result, err := evaluator.EvaluateSource(sourceData)
if err != nil {
    log.Fatal(err)
}
fmt.Printf("%s: %s (%.2f)\n", result.SourceID, result.Grade, result.TotalScore)
```

## 扩展方向

### 短期优化
1. **更智能的事实提取**：使用 NLP 技术提取实体和关系
2. **更准确的情感分析**：集成 spaCy 或 transformers
3. **网络传播分析**：追踪信源在社交媒体的传播路径

### 长期规划
1. **机器学习模型**：基于历史数据训练评分模型
2. **实时评价**：流式处理新文章，实时更新评分
3. **可视化界面**：Web 界面展示信源排名和趋势

## 文件清单

```
/home/wenyx/.openclaw/workspace/global-intel/src/collectors/
├── scoring.py              # 评分算法（核心）
├── evaluator.py            # 评价器主模块（核心）
├── evaluator.go            # Go 语言接口
├── README_EVALUATOR.md     # 使用说明
├── IMPLEMENTATION_SUMMARY.md  # 实现总结（本文件）
├── requirements.txt        # Python 依赖
└── source_evaluations.db   # SQLite 数据库（运行时生成）
```

## 与系统集成

### 在 rss.go 中调用
```go
// 采集 RSS 后评价信源
articles := fetchRSS(source)
score, err := evaluator.EvaluateSource(SourceData{
    SourceID: source.ID,
    SourceInfo: source.Info,
    Articles: articles,
})

// 根据等级决定更新频率
if score.Grade == "S" {
    schedule.UpdateInterval(source.ID, 5*time.Minute)
} else if score.Grade == "C" {
    schedule.DisableSource(source.ID)
}
```

### 定时评价任务
```bash
# crontab - 每 6 小时评价一次
0 */6 * * * cd /path/to/global-intel/src/collectors && python3 -c "
from evaluator import SourceEvaluator
evaluator = SourceEvaluator()
# 从数据库加载所有信源并重新评价
"
```

## 注意事项

1. **首次评价**：新信源需要至少 1 篇文章
2. **交叉验证**：多个信源同时评价准确性更高
3. **数据库备份**：定期备份 `source_evaluations.db`
4. **Python 版本**：需要 Python 3.8+

---

**实现完成时间**: 2026-03-02  
**实现者**: 评价组 - 信源评价体系  
**状态**: ✓ 完成
