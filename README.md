# 全球情报系统

**Global Intelligence System - 自动化全球资讯采集、分析、知识图谱构建系统**

## 🎯 项目简介

全球情报系统是一个自动化的全球资讯采集和分析系统，具备以下功能：

- **多信源采集**：RSS、官方 API、网页爬虫，支持 20+ 信源
- **智能处理**：数据清洗、实体识别、关系抽取、事件检测
- **知识图谱**：Neo4j 图数据库存储，支持复杂关系查询
- **大模型分析**：支持 OpenAI/Claude/通义千问，自动验证图谱正确性
- **情报报告**：每日/每周自动生成情报报告
- **信源评价**：4 维度评分系统，自动优胜劣汰

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    配置与调度中心                            │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌──────────────┐
│   数据采集层   │     │   数据处理层   │     │   应用服务层  │
│  (Go +5 采集器) │     │ (Python+4 处理器)│     │  (4 个服务)   │
├───────────────┤     ├───────────────┤     ├──────────────┤
│ • RSS Feed    │     │ • 数据清洗    │     │ • 报告生成    │
│ • 官方 API     │     │ • 实体识别    │     │ • 订阅管理    │
│ • 网页爬虫     │     │ • 关系抽取    │     │ • 推送服务    │
│ • 信源评价     │     │ • 事件检测    │     │ • REST API    │
└───────────────┘     └───────────────┘     └──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │   知识图谱层       │
                    │   (Neo4j + APOC)  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │   大模型层         │
                    │ (OpenAI/通义)     │
                    └───────────────────┘
```

## 🚀 快速开始

### 1. 环境要求

- Docker & Docker Compose
- Python 3.10+
- Go 1.21+

### 2. 安装依赖

```bash
# Python 依赖
pip3 install -r requirements.txt

# Go 依赖
cd src/collectors
go mod download
```

### 3. 启动 Neo4j

```bash
docker-compose up -d
```

**访问**: http://localhost:7474  
**用户名**: `neo4j`  
**密码**: `global_intel_2026`

### 4. 配置信源

编辑 `config/sources.yaml` 添加信源：

```yaml
sources:
  - name: 中国政府网
    url: http://www.gov.cn/zhengce/xxgkpub/gwygb/gwygb2026/index.htm
    type: crawler
    category: policy
    country: cn
    enabled: true
```

### 5. 配置大模型

编辑 `config/llm_config.yaml`：

```yaml
providers:
  qwen:
    enabled: true
    api_key: your-dashscope-api-key
    model: qwen-plus
```

### 6. 启动系统

```bash
# 启动调度器
python3 src/main.py scheduler start

# 查看日志
tail -f logs/global_intel.log
```

## 📊 核心功能

### 数据采集

- **RSS 采集器**：支持 RSS 2.0/Atom，并发采集
- **API 采集器**：支持多种认证方式
- **网页爬虫**：CSS 选择器，自动去重
- **信源评价**：4 维度评分，自动优胜劣汰

### 数据处理

- **数据清洗**：HTML 移除、去重、质量评分
- **实体识别**：6 种实体（GPE/GOV_ORG/ORG/PERSON/EVENT/LAW_POLICY）
- **关系抽取**：5 种关系（隶属于/位于/发布/影响/合作）
- **事件检测**：5 种事件类型，严重程度分级

### 知识图谱

- **Neo4j 存储**：图数据库存储实体和关系
- **APOC 插件**：支持复杂图算法
- **图谱验证**：大模型定期检测正确性

### 大模型分析

- **多提供商支持**：OpenAI/Claude/通义千问
- **图谱验证**：检测实体和关系的事实错误
- **报告生成**：每日/每周情报报告

## 📁 项目结构

```
global-intel/
├── config/                    # 配置文件
│   ├── config.yaml           # 主配置
│   ├── schedule.yaml         # 调度配置
│   ├── sources.yaml          # 信源配置
│   └── llm_config.yaml       # 大模型配置
├── src/
│   ├── collectors/           # 采集层 (Go)
│   ├── processors/           # 处理层 (Python)
│   ├── knowledge/            # 知识图谱
│   ├── llm/                  # 大模型
│   └── services/             # 应用服务
├── data/
│   ├── raw/                  # 原始数据
│   ├── processed/            # 处理后的数据
│   └── neo4j/                # Neo4j 数据（持久化）
├── logs/                     # 日志目录
├── scripts/                  # 运维脚本
├── docker-compose.yml        # Docker 配置
├── requirements.txt          # Python 依赖
└── go.mod                    # Go 依赖
```

## 📈 运行效果

### 数据采集（每 5-30 分钟）

```
[INFO] RSS Collector: 从 reuters.com 采集 15 篇文章
[INFO] API Collector: 从 gov.cn 采集 5 篇政策
[INFO] Evaluator: 评估 3 个信源，S 级 2 个，A 级 1 个
```

### 数据处理（每 30-60 分钟）

```
[INFO] Cleaner: 清洗 28 篇文章，去重 3 篇，平均质量 0.85
[INFO] EntityRecognizer: 识别 156 个实体
[INFO] RelationExtractor: 抽取 89 个关系
[INFO] EventDetector: 检测到 5 个事件（2 个 critical）
```

### 知识图谱（每 6 小时）

```
[INFO] GraphBuilder: 更新图谱，新增 50 个节点，120 条边
[INFO] GraphValidator: 验证完成，发现 2 个潜在错误
```

## 🔧 配置说明

### 信源评价系统

| 维度 | 权重 | 说明 |
|------|------|------|
| 准确性 | 30% | 与其他信源交叉验证 |
| 真实性 | 25% | 域名/作者/引用验证 |
| 客观性 | 25% | 情感分析，偏见检测 |
| 重大性 | 20% | 被引用次数，传播范围 |

**信源分级**:
- **S 级 (90-100)**: 优先采用，高频更新
- **A 级 (80-89)**: 正常采用，标准更新
- **B 级 (70-79)**: 谨慎采用，降低频率
- **C 级 (<70)**: 淘汰，连续 3 次自动移除

### 调度频率

| 层级 | 任务 | 频率 |
|------|------|------|
| 采集层 | RSS 订阅 | 每 5 分钟 |
| 采集层 | 官方 API | 每 15 分钟 |
| 采集层 | 网页爬虫 | 每 30 分钟 |
| 处理层 | 数据清洗 | 每 30 分钟 |
| 处理层 | 实体识别 | 每小时 |
| 服务层 | 知识图谱 | 每 6 小时 |
| 服务层 | 大模型分析 | ≤每小时 |
| 服务层 | 报告生成 | 每天 8 点 |

## 📞 技术支持

### 日志文件

- **主日志**: `logs/global_intel.log`
- **采集日志**: `logs/collectors.log`
- **处理日志**: `logs/processors.log`
- **大模型日志**: `logs/llm.log`

### API 端点

启动 API 服务后访问：

```bash
cd src/services
python3 api.py
```

- **Swagger UI**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **信源列表**: http://localhost:8000/api/sources
- **实体查询**: http://localhost:8000/api/entities
- **关系查询**: http://localhost:8000/api/relations
- **事件列表**: http://localhost:8000/api/events

## 📄 许可证

MIT License

## 🙏 致谢

- Neo4j 团队
- spaCy 团队
- OpenAI/Anthropic/阿里云

---

**版本**: v0.1  
**最后更新**: 2026-03-02  
**作者**: 老文的助理
