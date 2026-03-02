# 情报服务系统

提供报告生成、订阅管理、推送服务的完整解决方案。

## 📁 目录结构

```
services/
├── report.py          # 报告生成服务
├── subscribe.py       # 订阅管理系统
├── notifier.py        # 推送服务
├── api.py            # REST API 接口
├── templates/        # 报告模板
│   ├── daily_report.txt
│   └── weekly_report.txt
├── requirements.txt  # Python 依赖
└── README.md         # 本文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/wenyx/.openclaw/workspace/global-intel/src/services
pip install -r requirements.txt
```

### 2. 启动 API 服务

```bash
python api.py
```

API 将在 `http://localhost:8000` 启动

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

## 📊 功能模块

### 1. 报告生成 (`report.py`)

**功能：**
- 生成每日情报报告
- 生成每周情报报告
- 支持自定义模板
- 自动保存报告历史

**使用示例：**

```python
from report import ReportGenerator

generator = ReportGenerator()

# 生成每日报告
daily_report = generator.generate_daily_report()
print(f"报告 ID: {daily_report.report_id}")
print(f"标题：{daily_report.title}")

# 生成每周报告
weekly_report = generator.generate_weekly_report()

# 获取已有报告
report = generator.get_report("daily_20260302")

# 列出所有报告
reports = generator.list_reports()
```

### 2. 订阅管理 (`subscribe.py`)

**功能：**
- 用户注册与管理
- 订阅类型管理（每日/每周/实时）
- 用户偏好设置
- 订阅统计

**使用示例：**

```python
from subscribe import SubscriptionManager

manager = SubscriptionManager()

# 创建用户
user = manager.add_user(
    user_id="user001",
    username="测试用户",
    email="user@example.com",
    discord_id="123456789"
)

# 订阅每日报告
manager.subscribe("user001", "daily")

# 获取用户订阅
subscriptions = manager.get_user_subscriptions("user001")

# 获取某类订阅的所有用户
subscribers = manager.get_subscribers("daily")

# 统计信息
stats = manager.get_stats()
print(f"总用户数：{stats['total_users']}")
```

### 3. 推送服务 (`notifier.py`)

**功能：**
- Discord 消息推送（Webhook/Bot）
- 邮件推送（SMTP）
- 批量推送
- 推送历史记录

**配置示例：**

```python
from notifier import Notifier

notifier = Notifier()

# 配置 Discord
notifier.configure_discord(
    webhook_url="https://discord.com/api/webhooks/...",
    default_channel="123456789"
)

# 配置邮件
notifier.configure_email(
    smtp_server="smtp.example.com",
    smtp_port=587,
    username="user@example.com",
    password="password",
    from_address="user@example.com"
)
```

**推送示例：**

```python
import asyncio
from notifier import NotificationMessage

# 发送 Discord 消息
async def send_discord():
    message = NotificationMessage(
        title="新报告发布",
        content="每日情报报告已生成，请查看。",
        priority="high"
    )
    result = await notifier.send_discord(message, channel_id="123456789")
    print(f"推送成功：{result.success}")

asyncio.run(send_discord())

# 发送邮件
result = notifier.send_email(
    message="报告内容",
    to_address="user@example.com",
    subject="每日情报报告"
)

# 批量推送
recipients = [
    {"channel": "discord", "recipient": "channel1"},
    {"channel": "email", "recipient": "user@example.com"}
]
results = await notifier.broadcast(message, recipients)
```

### 4. REST API (`api.py`)

**端点概览：**

#### 健康检查
- `GET /` - API 信息
- `GET /health` - 健康检查

#### 报告管理
- `POST /reports/generate` - 生成报告
- `GET /reports` - 列出报告
- `GET /reports/{report_id}` - 获取报告
- `GET /reports/{report_id}/download` - 下载报告

#### 用户管理
- `POST /users` - 创建用户
- `GET /users` - 列出用户
- `GET /users/{user_id}` - 获取用户
- `PUT /users/{user_id}` - 更新用户
- `DELETE /users/{user_id}` - 删除/停用用户

#### 订阅管理
- `POST /users/{user_id}/subscribe` - 订阅
- `DELETE /users/{user_id}/unsubscribe` - 取消订阅
- `GET /users/{user_id}/subscriptions` - 用户订阅列表
- `GET /subscriptions/{type}` - 订阅者列表
- `GET /stats` - 统计信息

#### 推送服务
- `POST /notify` - 发送通知
- `POST /notify/broadcast` - 批量推送
- `POST /reports/{report_id}/send` - 发送报告
- `GET /notify/stats` - 推送统计

#### 模板管理
- `GET /templates` - 列出模板
- `GET /templates/{name}` - 获取模板
- `PUT /templates/{name}` - 保存模板
- `DELETE /templates/{name}` - 删除模板

**API 使用示例：**

```bash
# 生成每日报告
curl -X POST http://localhost:8000/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"report_type": "daily"}'

# 创建用户
curl -X POST http://localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user001",
    "username": "测试用户",
    "email": "user@example.com"
  }'

# 订阅报告
curl -X POST http://localhost:8000/users/user001/subscribe \
  -H "Content-Type: application/json" \
  -d '{"subscription_type": "daily"}'

# 发送通知
curl -X POST http://localhost:8000/notify \
  -H "Content-Type: application/json" \
  -d '{
    "title": "测试通知",
    "content": "这是一条测试消息",
    "channel": "discord",
    "recipient": "channel_id"
  }'
```

## 🔧 配置文件

### Notifier 配置 (`notifier_config.json`)

首次运行时会自动创建默认配置：

```json
{
  "discord": {
    "enabled": true,
    "webhook_url": "",
    "bot_token": "",
    "default_channel": ""
  },
  "email": {
    "enabled": false,
    "smtp_server": "smtp.example.com",
    "smtp_port": 587,
    "username": "",
    "password": "",
    "from_address": "",
    "use_tls": true
  },
  "retry": {
    "max_attempts": 3,
    "delay_seconds": 5
  }
}
```

## 📝 数据目录结构

```
services/
├── data/
│   ├── market_YYYYMMDD.json    # 市场数据
│   ├── news_YYYYMMDD.json      # 新闻数据
│   └── reports/                # 生成的报告
│       ├── daily_YYYYMMDD.json
│       ├── daily_YYYYMMDD.txt
│       └── weekly_...
├── subscribers/
│   ├── users.json              # 用户数据
│   └── subscriptions.json      # 订阅关系
└── delivery_history.json       # 推送历史
```

## 🎯 典型工作流

### 1. 每日自动报告流程

```
1. 定时任务触发 (cron/heartbeat)
   ↓
2. 调用 ReportGenerator.generate_daily_report()
   ↓
3. 收集当日数据并生成报告
   ↓
4. 从 SubscriptionManager 获取订阅者
   ↓
5. 调用 Notifier.send_report() 推送
   ↓
6. 记录推送结果
```

### 2. 用户订阅流程

```
1. 用户通过 API 注册
   ↓
2. 选择订阅类型（每日/每周）
   ↓
3. 设置推送偏好（Discord/邮件）
   ↓
4. 系统自动在报告生成时推送
```

## 🧪 测试

每个模块都包含测试代码，可直接运行：

```bash
# 测试报告生成
python report.py

# 测试订阅管理
python subscribe.py

# 测试推送服务
python notifier.py
```

## 📋 注意事项

1. **首次运行**：会自动创建必要的目录和配置文件
2. **Discord 推送**：需要配置 Webhook URL 或 Bot Token
3. **邮件推送**：需要配置 SMTP 服务器信息
4. **数据安全**：生产环境请妥善保存配置文件，不要提交到版本控制
5. **性能优化**：大量用户推送时使用 `BackgroundTasks` 异步处理

## 🔄 集成示例

### 与公告监控系统集成

```python
from announcement_monitor import AnnouncementMonitor
from services.report import ReportGenerator
from services.subscribe import SubscriptionManager
from services.notifier import Notifier

# 监控公告
monitor = AnnouncementMonitor()
announcements = monitor.get_latest_announcements()

# 生成报告
generator = ReportGenerator()
report = generator.generate_daily_report()

# 推送给订阅者
notifier = Notifier()
manager = SubscriptionManager()
subscribers = manager.get_subscribers("daily")

# 构建接收者列表
recipients = []
for sub in subscribers:
    if sub.discord_id:
        recipients.append({"channel": "discord", "recipient": sub.discord_id})
    if sub.email:
        recipients.append({"channel": "email", "recipient": sub.email})

# 推送
await notifier.broadcast(report_message, recipients)
```

## 📞 支持

遇到问题请查看：
- API 文档：`http://localhost:8000/docs`
- 日志文件：检查各模块生成的数据文件
- 健康检查：`http://localhost:8000/health`

---

**版本**: 1.0.0  
**最后更新**: 2026-03-02
