# 大模型接口与分析模块

情报分析系统的大模型接口层，支持 OpenAI/GPT/Claude/通义千问等主流大模型。

## 功能模块

### 1. 大模型抽象接口 (`provider.py`)

- **LLMProvider**: 抽象基类，定义统一接口
- **ModelConfig**: 模型配置数据类
- **ProviderFactory**: 工厂模式创建提供商实例
- 支持的提供商：OpenAI, Claude, Qwen (通义千问)

### 2. OpenAI 实现 (`openai_provider.py`)

- 完整的 OpenAI API 封装
- 自动成本计算（基于官方定价）
- 支持 GPT-3.5/GPT-4/GPT-4o 系列模型
- 懒加载客户端，节省资源

### 3. 分析任务 (`analyzer.py`)

#### 图谱验证
检测知识图谱的事实错误：
- 实体准确性验证
- 关系逻辑性检查
- 矛盾识别
- 证据支持

#### 关联验证
验证实体间关联的合理性：
- 关系类型合理性分析
- 逻辑矛盾检测
- 替代解释提供

#### 报告生成
生成每日/每周情报报告：
- 执行摘要
- 关键发现（带重要性评级）
- 行动建议

### 4. 配置文件 (`llm_config.yaml`)

- 大模型连接配置
- 频率限制设置
- 预算管理
- 任务参数
- 日志配置

## 快速开始

### 安装依赖

```bash
pip install openai pyyaml
```

### 配置 API 密钥

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### 使用示例

```python
from analyzer import IntelligenceAnalyzer, Entity, Relation

# 初始化分析器
analyzer = IntelligenceAnalyzer("llm_config.yaml")

# 查看状态
print(analyzer.get_status())

# 图谱验证
entities = [
    Entity(id="1", name="苹果公司", type="Organization", properties={"industry": "科技"}),
    Entity(id="2", name="Tim Cook", type="Person", properties={"role": "CEO"})
]
relations = [
    Relation(id="r1", source="2", target="1", type="WORKS_FOR", properties={})
]

result = analyzer.verify_knowledge_graph(entities, relations)
print(f"验证结果：有效={result.is_valid}, 置信度={result.confidence}")

# 关联验证
relation_result = analyzer.verify_relation_validity(
    entities[0], entities[1], "WORKS_FOR"
)

# 生成报告
data = {"key_findings": ["发现 1", "发现 2"]}
report = analyzer.generate_report("daily", data, period_days=1)
print(f"报告摘要：{report.summary}")
```

## 频率限制

系统自动管理调用频率：

- **最小间隔**: 3600 秒（1 小时）
- **每日最大调用**: 24 次
- **每日预算**: $10.00

状态自动保存在 `analyzer_state.json` 中。

## 成本估算

基于 OpenAI 官方定价（每 1000 tokens）：

| 模型 | 输入 | 输出 |
|------|------|------|
| gpt-4o-mini | $0.00015 | $0.0006 |
| gpt-4o | $0.005 | $0.015 |
| gpt-4-turbo | $0.01 | $0.03 |
| gpt-4 | $0.03 | $0.06 |

## 扩展其他提供商

创建新的提供商类（如 `claude_provider.py`）：

```python
from provider import LLMProvider, ModelConfig, ModelResponse

class ClaudeProvider(LLMProvider):
    def chat(self, messages, **kwargs) -> ModelResponse:
        # 实现 Claude API 调用
        pass
    
    def calculate_cost(self, prompt_tokens, completion_tokens) -> float:
        # 实现成本计算
        pass
    
    def get_model_info(self) -> dict:
        # 返回模型信息
        pass
```

## 文件结构

```
llm/
├── provider.py          # 抽象接口
├── openai_provider.py   # OpenAI 实现
├── claude_provider.py   # Claude 实现（待实现）
├── qwen_provider.py     # 通义千问实现（待实现）
├── analyzer.py          # 分析任务
├── llm_config.yaml      # 配置文件
├── analyzer_state.json  # 状态文件（运行时生成）
└── README.md            # 本文档
```

## 注意事项

1. **API 密钥安全**: 使用环境变量，不要硬编码在配置文件中
2. **预算控制**: 系统会自动跟踪支出，超出预算会停止调用
3. **错误处理**: 所有方法都包含异常处理，解析失败时返回保守结果
4. **状态持久化**: 调用状态自动保存，重启后继续跟踪

## License

MIT
