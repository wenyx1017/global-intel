# 知识图谱系统

基于 Neo4j 的知识图谱系统，支持实体管理、关系构建、图谱查询和数据验证。

## 快速开始

### 1. 启动 Neo4j 数据库

```bash
cd /home/wenyx/.openclaw/workspace/global-intel/src/knowledge
docker-compose up -d
```

等待 Neo4j 启动完成后，可通过以下方式访问：
- Web 界面：http://localhost:7474
- 用户名：neo4j
- 密码：knowledge_graph_2024

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 使用示例

#### 构建图谱

```python
from builder import get_builder

with get_builder() as builder:
    # 创建实体
    china = builder.create_gpe("中国", "CN", "中华人民共和国")
    tencent = builder.create_org("腾讯", "company", "互联网")
    
    # 创建关系
    builder.link_gpe_location("腾讯", "中国")
    
    # 构建示例图谱
    builder.build_sample_graph()
```

#### 查询图谱

```python
from query import get_query_interface

with get_query_interface() as query:
    # 搜索实体
    results = query.search_by_name("中国")
    
    # 获取统计信息
    stats = query.get_statistics()
    
    # 查询组织关联
    connections = query.get_org_connections("腾讯")
```

#### 验证数据

```python
from validator import get_validator

with get_validator() as validator:
    # 验证实体
    result = validator.validate_entity_exists("中国", "GPE")
    
    # 验证关系
    rel_result = validator.validate_relationship("腾讯", "中国", "LOCATED_IN")
    
    # 获取验证报告
    report = validator.get_validation_report()
```

## 实体类型

| 类型 | 说明 | 示例 |
|------|------|------|
| GPE | 国家/地区 | 中国、美国、北京市 |
| GOV_ORG | 政府机构 | 国家发改委、工信部 |
| ORG | 公司/组织 | 腾讯、阿里巴巴 |
| PERSON | 人物 | 张三、李四 |
| EVENT | 事件 | 数字经济峰会 |
| LAW_POLICY | 政策/法规 | 数据安全法 |

## 关系类型

| 关系 | 说明 | 方向 |
|------|------|------|
| BELONGS_TO | 隶属于 | 子->父 |
| LOCATED_IN | 位于 | 实体->地点 |
| PUBLISHES | 发布 | 机构->政策 |
| IMPLEMENTS | 实施 | 机构->政策 |
| AFFECTS | 影响 | 政策->目标 |
| AFFECTED_BY | 被影响 | 目标->政策 |
| COOPERATES_WITH | 合作 | 组织<->组织 |
| CONFLICTS_WITH | 对抗 | 组织<->组织 |

## LLM 调用接口

验证器提供简洁的 LLM 调用接口：

```python
from validator import validate_entity, validate_relationship_llm, get_validation_report

# 验证实体
result = validate_entity("中国", "GPE")

# 验证关系
result = validate_relationship_llm("腾讯", "中国", "LOCATED_IN")

# 获取报告
report = get_validation_report()
```

## 文件结构

```
knowledge/
├── docker-compose.yml      # Neo4j 部署配置
├── requirements.txt        # Python 依赖
├── graph.py               # Neo4j 基础操作
├── builder.py             # 图谱构建器
├── query.py               # 图谱查询接口
├── validator.py           # 图谱验证接口
└── README.md              # 本文档
```

## 配置说明

Neo4j 连接配置（可在代码中修改）：
- URI: bolt://localhost:7687
- 用户名：neo4j
- 密码：knowledge_graph_2024

## 注意事项

1. 首次运行需要先启动 Docker 容器
2. 确保 7474 和 7687 端口未被占用
3. 生产环境请修改默认密码
4. 定期备份数据（Neo4j 数据卷）
