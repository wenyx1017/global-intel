#!/bin/bash
# 全球情报系统 - 调度器启动脚本
# Global Intelligence System - Scheduler Startup Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 加载环境变量
if [ -f ".env.local" ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
elif [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动调度器
echo "启动全球情报系统调度器..."
python src/scheduler.py --config config.yaml "$@"
