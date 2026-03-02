#!/bin/bash
# 全球情报系统 - 初始化脚本
# Global Intelligence System - Initialization Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "======================================"
echo "  全球情报系统 - 初始化"
echo "  Global Intelligence System Init"
echo "======================================"

cd "$PROJECT_DIR"

# 1. 创建必要目录
echo "[1/5] 创建数据目录..."
mkdir -p data/{raw,processed,cache}
mkdir -p logs
mkdir -p backups

# 2. 检查 Python 依赖
echo "[2/5] 检查 Python 环境..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "错误：未找到 Python"
    exit 1
fi

echo "  使用 Python: $($PYTHON_CMD --version)"

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "  创建虚拟环境..."
    $PYTHON_CMD -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "  安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 下载 spaCy 模型
echo "  下载 spaCy 语言模型..."
python -m spacy download zh_core_web_sm || true
python -m spacy download en_core_web_sm || true

# 3. 检查 Go 环境
echo "[3/5] 检查 Go 环境..."
if command -v go &> /dev/null; then
    echo "  Go 版本：$(go version)"
    echo "  下载 Go 依赖..."
    go mod download
else
    echo "  警告：未找到 Go，跳过 Go 依赖安装"
fi

# 4. 检查 Redis（可选）
echo "[4/5] 检查 Redis..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "  Redis: 运行中"
    else
        echo "  警告：Redis 未运行"
    fi
else
    echo "  警告：未安装 Redis"
fi

# 5. 检查 Neo4j（可选）
echo "[5/5] 检查 Neo4j..."
if command -v neo4j &> /dev/null; then
    echo "  Neo4j: 已安装"
else
    echo "  警告：未安装 Neo4j，将使用 NetworkX 作为替代"
fi

# 6. 设置环境变量
echo ""
echo "设置环境变量..."
cat > .env << 'EOF'
# 全球情报系统 - 环境变量
# 复制此文件为 .env.local 并填入实际值

# 大模型 API
LLM_API_KEY=your_api_key_here

# 数据库
DB_PASSWORD=your_db_password
NEO4J_PASSWORD=your_neo4j_password

# 通知
EMAIL_USER=your_email@example.com
EMAIL_PASSWORD=your_email_password
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...

# API 密钥
API_KEY_1=your_api_key

# WeChat（可选）
WECHAT_CORP_ID=
WECHAT_AGENT_ID=
WECHAT_SECRET=
EOF

echo ""
echo "======================================"
echo "  初始化完成！"
echo "======================================"
echo ""
echo "下一步："
echo "1. 编辑 .env.local 文件，填入实际的 API 密钥和密码"
echo "2. 运行：source venv/bin/activate"
echo "3. 启动系统：python src/main.py"
echo ""
echo "配置文件位置："
echo "  - 主配置：config.yaml"
echo "  - 调度配置：config/schedule.yaml"
echo "  - 信源配置：config/sources.yaml"
echo ""
