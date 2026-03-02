#!/bin/bash
# 全球情报系统启动脚本

set -e

echo "=========================================="
echo "  全球情报系统 - 启动脚本"
echo "  Global Intelligence System"
echo "=========================================="
echo ""

PROJECT_ROOT="/home/wenyx/.openclaw/workspace/global-intel"
cd "$PROJECT_ROOT"

# 检查 Neo4j
echo "🐳 检查 Neo4j..."
if docker ps | grep -q global_intel_neo4j; then
    echo "  ✅ Neo4j 运行正常"
else
    echo "  ⚠️  Neo4j 未运行，正在启动..."
    docker-compose up -d
    sleep 10
fi
echo ""

# 检查 Python 依赖
echo "📦 检查 Python 依赖..."
pip3 install -q -r requirements.txt 2>/dev/null || echo "  ⚠️  部分依赖可能未安装"
echo "  ✅ Python 依赖就绪"
echo ""

# 创建日志目录
mkdir -p logs
echo "  ✅ 日志目录就绪"
echo ""

# 启动调度器
echo "🚀 启动调度器..."
echo "  日志文件：logs/scheduler.log"
echo "  按 Ctrl+C 停止"
echo ""

python3 src/main.py scheduler start
