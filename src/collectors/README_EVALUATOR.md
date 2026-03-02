# 信源评价系统使用说明

## 文件结构

```
collectors/
├── evaluator.py        # 评价器主模块
├── scoring.py          # 评分算法模块
└── source_evaluations.db  # SQLite 数据库（运行时生成）
```

## 评价维度

| 维度 | 权重 | 说明 |
|------|------|------|
| **准确性** | 30% | 与其他信源交叉验证 |
| **真实性** | 25% | 域名、作者、引用验证 |
| **客观性** | 25% | 情感分析、偏见检测 |
| **重大性** | 20% | 传播度、引用次数 |

## 信源分级

| 等级 | 分数 | 处理策略 |
|------|------|----------|
| **S 级** | 90-100 | 优先采用，高频更新 |
| **A 级** | 80-89 | 正常采用，标准更新 |
| **B 级** | 70-79 | 谨慎采用，降低频率 |
| **C 级** | <70 | 淘汰，移除信源 |

## 使用示例

### 1. 基本使用

```python
from evaluator import SourceEvaluator

# 创建评价器
evaluator = SourceEvaluator(db_path="source_evaluations.db")

# 准备信源数据
sources_data = [
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
                "title": "Market Update",
                "content": "Stock markets rose 2.5% today...",
                "published_at": datetime.now(),
                "citations": 100,
                "views": 50000,
                "shares": 1000
            }
        ]
    }
]

# 执行评价
scores = evaluator.evaluate_all_sources(sources_data)

# 查看结果
for score in scores:
    print(f"{score.source_id}: {score.grade} ({score.total_score})")
```

### 2. 单独评价单个信源

```python
from evaluator import SourceEvaluator

evaluator = SourceEvaluator()

score = evaluator.evaluate_source(
    source_id="reuters",
    source_info={...},
    articles=[...],
    other_sources=[...]  # 用于交叉验证
)

print(f"等级：{score.grade}")
print(f"准确性：{score.accuracy}")
print(f"真实性：{score.authenticity}")
print(f"客观性：{score.objectivity}")
print(f"重大性：{score.importance}")
```

### 3. 查询评价结果

```python
from evaluator import SourceEvaluator

evaluator = SourceEvaluator()

# 获取某信源的最新等级
grade = evaluator.get_source_grade("reuters")

# 获取所有 S 级信源
s_sources = evaluator.get_sources_by_grade("S")

# 获取待淘汰信源（C 级）
elimination_candidates = evaluator.get_elimination_candidates()

# 获取评价趋势
trend = evaluator.db.get_evaluation_trend("reuters", days=30)
```

### 4. 生成评价报告

```python
from evaluator import SourceEvaluator

evaluator = SourceEvaluator()
report = evaluator.generate_report()

print(f"总信源数：{report['total_sources']}")
print(f"等级分布：{report['grade_distribution']}")
print(f"平均分数：{report['average_scores']}")
print(f"Top 10 信源：{report['top_sources']}")
print(f"待淘汰信源：{report['elimination_candidates']}")
```

### 5. 便捷函数

```python
from evaluator import quick_evaluate

results = quick_evaluate(sources_data)

for result in results:
    print(f"{result['source_id']}: {result['grade']} - {result['total_score']}")
```

## 数据库结构

### evaluations 表
存储最新评价结果

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| source_id | TEXT | 信源 ID |
| accuracy | REAL | 准确性分数 |
| authenticity | REAL | 真实性分数 |
| objectivity | REAL | 客观性分数 |
| importance | REAL | 重大性分数 |
| total_score | REAL | 总分 |
| grade | TEXT | 等级 (S/A/B/C) |
| evaluated_at | TIMESTAMP | 评价时间 |

### evaluation_history 表
存储评价历史（用于趋势分析）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| source_id | TEXT | 信源 ID |
| total_score | REAL | 总分 |
| grade | TEXT | 等级 |
| evaluated_at | TIMESTAMP | 评价时间 |

### sources 表
存储信源基本信息

| 字段 | 类型 | 说明 |
|------|------|------|
| source_id | TEXT | 信源 ID（主键） |
| domain | TEXT | 域名 |
| author | TEXT | 作者 |
| established_date | TEXT | 成立时间 |
| status | TEXT | 状态 (active/pending_elimination/eliminated) |

## 自动淘汰机制

评价器会自动检查信源等级并更新状态：

1. **C 级信源** → 标记为 `pending_elimination`
2. **连续 3 次 C 级** → 标记为 `eliminated`

手动干预：

```python
# 提升信源等级（手动）
evaluator.promote_source("source_id")
```

## 评分算法细节

### 准确性 (30%)
- 与其他信源交叉验证关键事实（数字、日期等）
- 如果没有其他信源，基于文章质量评分：
  - 有具体数据支撑 (+20)
  - 有引用来源 (+20)
  - 文章长度适中 (+20)
  - 没有极端词汇 (+20)
  - 有明确发布时间 (+20)

### 真实性 (25%)
- 域名验证 (40 分)：可信域名满分，可疑 TLD 扣分
- 作者验证 (30 分)：知名机构满分，匿名作者低分
- 引用验证 (20 分)：引用次数越多分数越高
- 成立时间 (10 分)：信源越老越可信

### 客观性 (25%)
- 情感分析：检测正面/负面词汇比例
- 偏见检测：检测极端词汇和主观表达
- 越中立即分数越高

### 重大性 (20%)
- 引用次数 (40%)
- 阅读量 (30%)
- 分享数 (30%)
- 时效性加成（近期内容权重更高）

## 与系统集成

### 在数据采集层调用

```go
// Go 代码调用 Python 评价器
func evaluateSource(source Source) SourceScore {
    // 准备数据
    data := prepareEvaluationData(source)
    
    // 调用 Python 脚本
    cmd := exec.Command("python3", "evaluator.py", data)
    output, err := cmd.Output()
    
    // 解析结果
    var score SourceScore
    json.Unmarshal(output, &score)
    
    return score
}
```

### 定时评价任务

```bash
# cron 配置：每 6 小时评价一次
0 */6 * * * cd /path/to/collectors && python3 -c "
from evaluator import SourceEvaluator
evaluator = SourceEvaluator()
# 从数据库加载信源数据并评价
"
```

## 注意事项

1. **首次评价**：新信源需要至少 1 篇文章才能评价
2. **交叉验证**：多个信源同时评价时准确性更高
3. **数据库备份**：定期备份 `source_evaluations.db`
4. **性能优化**：大量信源时考虑批量评价

## 扩展评分算法

如需添加新的评分维度，修改 `scoring.py`：

```python
class SourceScorer:
    # 添加新维度
    WEIGHT_NEW_DIMENSION = 0.10
    
    # 调整现有权重（总和保持 1.0）
    WEIGHT_ACCURACY = 0.27
    WEIGHT_AUTHENTICITY = 0.23
    WEIGHT_OBJECTIVITY = 0.23
    WEIGHT_IMPORTANCE = 0.17
    
    def calculate_new_dimension(self, articles: List[Dict]) -> float:
        # 实现新维度评分
        pass
    
    def evaluate(self, ...):
        # 添加新维度到计算
        new_dimension = self.calculate_new_dimension(articles)
        
        return SourceScore(
            ...,
            new_dimension=new_dimension,
            total_score=None  # 自动计算
        )
```

---

**最后更新**: 2026-03-02
