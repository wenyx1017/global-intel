#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全球情报系统 - 主程序入口
Global Intelligence System - Main Entry Point

用法:
    python src/main.py [command] [options]

命令:
    init        初始化系统
    scheduler   启动调度器
    collector   运行采集器
    processor   运行处理器
    analyzer    运行分析器
    status      查看系统状态
"""

import os
import sys
import argparse
import signal
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger import get_logger, configure_logging
from src.scheduler import Scheduler


# 全局日志器
logger = get_logger(__name__)


def init_system(args):
    """初始化系统"""
    logger.info("初始化系统...")
    
    # 创建必要目录
    dirs = [
        "data/raw",
        "data/processed",
        "data/cache",
        "logs",
        "backups"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录：{dir_path}")
    
    # 检查配置文件
    config_files = [
        "config.yaml",
        "config/schedule.yaml",
        "config/sources.yaml"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            logger.info(f"配置文件存在：{config_file}")
        else:
            logger.warning(f"配置文件不存在：{config_file}")
    
    logger.info("系统初始化完成")


def run_scheduler(args):
    """运行调度器"""
    logger.info("启动调度器...")
    
    config_path = args.config if args.config else "config.yaml"
    
    # 创建调度器
    scheduler = Scheduler(config_path)
    
    # 处理信号
    def signal_handler(sig, frame):
        logger.info("收到停止信号，正在关闭...")
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动调度器
    scheduler.start(blocking=True)


def run_collector(args):
    """运行采集器"""
    logger.info("运行采集器...")
    # TODO: 实现采集器逻辑
    logger.info("采集器功能开发中...")


def run_processor(args):
    """运行处理器"""
    logger.info("运行处理器...")
    # TODO: 实现处理器逻辑
    logger.info("处理器功能开发中...")


def run_analyzer(args):
    """运行分析器"""
    logger.info("运行分析器...")
    # TODO: 实现分析器逻辑
    logger.info("分析器功能开发中...")


def show_status(args):
    """显示系统状态"""
    logger.info("系统状态")
    
    # 检查目录
    dirs = ["data", "logs", "config"]
    for dir_name in dirs:
        if Path(dir_name).exists():
            print(f"✓ {dir_name}/")
        else:
            print(f"✗ {dir_name}/ (不存在)")
    
    # 检查配置文件
    config_files = ["config.yaml", "config/schedule.yaml", "config/sources.yaml"]
    for config_file in config_files:
        if Path(config_file).exists():
            print(f"✓ {config_file}")
        else:
            print(f"✗ {config_file} (不存在)")
    
    # 检查环境
    print("\n环境检查:")
    print(f"  Python: {sys.version}")
    print(f"  工作目录：{os.getcwd()}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="全球情报系统 - Global Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # init 命令
    init_parser = subparsers.add_parser("init", help="初始化系统")
    init_parser.set_defaults(func=init_system)
    
    # scheduler 命令
    scheduler_parser = subparsers.add_parser("scheduler", help="启动调度器")
    scheduler_parser.add_argument("--config", type=str, help="配置文件路径")
    scheduler_parser.set_defaults(func=run_scheduler)
    
    # collector 命令
    collector_parser = subparsers.add_parser("collector", help="运行采集器")
    collector_parser.set_defaults(func=run_collector)
    
    # processor 命令
    processor_parser = subparsers.add_parser("processor", help="运行处理器")
    processor_parser.set_defaults(func=run_processor)
    
    # analyzer 命令
    analyzer_parser = subparsers.add_parser("analyzer", help="运行分析器")
    analyzer_parser.set_defaults(func=run_analyzer)
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查看系统状态")
    status_parser.set_defaults(func=show_status)
    
    # 解析参数
    args = parser.parse_args()
    
    # 加载配置
    config_path = Path("config.yaml")
    if config_path.exists():
        configure_logging(str(config_path))
    
    # 执行命令
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
