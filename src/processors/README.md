# 数据处理模块

数据清洗和实体识别处理器

## 文件说明

- `cleaner.py` - 数据清洗管道（文本规范化、去重）
- `entity.py` - 实体识别模块（基于 spaCy + 自定义规则）
- `entities.yaml` - 实体类型定义和标准化规则

## 安装依赖

```bash
# 基础依赖
pip install PyYAML

# 实体识别依赖（可选，但推荐）
pip install spacy

# 下载中文模型
python -m spacy download zh_core_web_sm

# 或英文模型
python -m spacy download en_core_web_sm
```

## 使用示例

### 数据清洗

```python
from cleaner import create_pipeline, clean_text, deduplicate_texts

# 创建清洗管道
pipeline = create_pipeline({
    'cleaner': {
        'remove_html': True,
        'normalize_whitespace': True
    },
    'deduplicator': {
        'strategy': 'normalized'
    }
})

# 单条清洗
result = pipeline.process("<p>中国国务院发布新政策</p>")
print(result['cleaned'])  # "中国国务院发布新政策"

# 批量去重
texts = ["阿里巴巴", "阿里", "阿里巴巴"]  # 重复
unique = deduplicate_texts(texts)
```

### 实体识别

```python
from entity import create_recognizer, recognize_entities

# 创建识别器
recognizer = create_recognizer(
    config_path='entities.yaml',
    language='zh'
)

# 识别实体
text = "中国国务院总理在两会宣布十四五规划"
result = recognizer.recognize(text)

for entity in result.entities:
    print(f"{entity.text} - {entity.label_name}")
    if entity.normalized:
        print(f"  标准化：{entity.normalized}")

# 按类型提取
persons = recognizer.extract_entities_by_type(text, ['PERSON'])
```

## 支持的实体类型

| 标签 | 名称 | 说明 |
|------|------|------|
| GPE | 国家/地区 | 国家、地区、行政区域 |
| GOV_ORG | 政府机构 | 政府部门、机构、委员会 |
| ORG | 公司/组织 | 企业、公司、非政府组织 |
| PERSON | 人物 | 个人姓名、职位人物 |
| EVENT | 事件 | 重要事件、会议、活动 |
| LAW_POLICY | 政策/法规 | 法律、法规、政策、条例 |

## 功能特性

### 数据清洗 (`cleaner.py`)

- ✅ HTML 标签移除
- ✅ 空白字符规范化
- ✅ 标点符号统一（全角转半角）
- ✅ URL 处理
- ✅ 质量评分
- ✅ 多级去重（精确、规范化、模糊匹配）

### 实体识别 (`entity.py`)

- ✅ spaCy NER 集成
- ✅ 自定义规则匹配
- ✅ 实体标准化（别名映射）
- ✅ 重叠实体合并
- ✅ 置信度评分
- ✅ 批量处理

## 配置说明

### entities.yaml 结构

```yaml
entity_types:
  - name: GPE
    label: 国家/地区
    examples:
      - 中国
      - 美国

normalization_rules:
  GPE:
    aliases:
      中国大陆：中国
      USA: 美国

deduplication:
  strategy: normalized_name
  similarity_threshold: 0.85
```

## 性能参考

- 单条文本清洗：~1-5ms
- 单条实体识别：~10-50ms（取决于 spaCy 模型）
- 批量处理：支持并发优化
