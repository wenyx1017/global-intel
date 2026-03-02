#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志系统 - 统一的日志管理模块
Logging System - Unified Logging Management

支持：
- 多级别日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 文件日志（支持轮转）
- 控制台日志（支持彩色）
- 结构化日志（JSON 格式）
- 分布式追踪（可选）
"""

import os
import sys
import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Optional, Dict, Any
from pathlib import Path
import yaml


class ColoredFormatter(logging.Formatter):
    """彩色控制台格式化器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器（JSON 格式）"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加额外字段
        if hasattr(record, 'extra_data'):
            log_data['data'] = record.extra_data
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class Logger:
    """自定义日志器"""
    
    def __init__(self, name: str, config: dict = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if self.logger.handlers:
            return
        
        # 加载配置
        self.config = config or self._load_default_config()
        
        # 设置 handlers
        self._setup_handlers()
    
    def _load_default_config(self) -> dict:
        """加载默认配置"""
        config_path = Path(__file__).parent.parent / "config.yaml"
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('logging', {})
            except Exception as e:
                print(f"加载日志配置失败：{e}")
        
        # 返回默认配置
        return {
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S',
            'file': {
                'enabled': True,
                'path': './logs/global_intel.log',
                'max_size': 10485760,
                'backup_count': 5,
                'rotation': 'daily'
            },
            'console': {
                'enabled': True,
                'colorize': True
            },
            'structured': {
                'enabled': False,
                'path': './logs/structured.json'
            }
        }
    
    def _setup_handlers(self):
        """设置日志处理器"""
        log_format = self.config.get('format', '%(asctime)s [%(levelname)s] %(name)s: %(message)s')
        date_format = self.config.get('date_format', '%Y-%m-%d %H:%M:%S')
        level = getattr(logging, self.config.get('level', 'INFO').upper())
        
        # 1. 控制台处理器
        console_config = self.config.get('console', {})
        if console_config.get('enabled', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            
            if console_config.get('colorize', True):
                console_formatter = ColoredFormatter(log_format, date_format)
            else:
                console_formatter = logging.Formatter(log_format, date_format)
            
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        # 2. 文件处理器
        file_config = self.config.get('file', {})
        if file_config.get('enabled', True):
            file_path = file_config.get('path', './logs/global_intel.log')
            
            # 确保目录存在
            log_dir = os.path.dirname(file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # 根据轮转类型选择 handler
            rotation = file_config.get('rotation', 'daily').lower()
            max_size = file_config.get('max_size', 10485760)
            backup_count = file_config.get('backup_count', 5)
            
            if rotation == 'size':
                file_handler = RotatingFileHandler(
                    file_path, maxBytes=max_size, backupCount=backup_count, encoding='utf-8'
                )
            else:
                file_handler = TimedRotatingFileHandler(
                    file_path, when='D', interval=1, backupCount=backup_count, encoding='utf-8'
                )
            
            file_handler.setLevel(level)
            file_formatter = logging.Formatter(log_format, date_format)
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        
        # 3. 结构化日志处理器
        structured_config = self.config.get('structured', {})
        if structured_config.get('enabled', False):
            struct_path = structured_config.get('path', './logs/structured.json')
            
            # 确保目录存在
            struct_dir = os.path.dirname(struct_path)
            if struct_dir:
                os.makedirs(struct_dir, exist_ok=True)
            
            struct_handler = RotatingFileHandler(
                struct_path, maxBytes=10485760, backupCount=3, encoding='utf-8'
            )
            struct_handler.setLevel(level)
            struct_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(struct_handler)
    
    def _log(self, level: int, msg: str, extra: dict = None, **kwargs):
        """内部日志方法"""
        # 添加额外数据
        if extra:
            # 创建新的 record 以添加 extra_data
            old_factory = logging.getLogRecordFactory()
            
            def record_factory(*args, **kw):
                record = old_factory(*args, **kw)
                record.extra_data = extra
                return record
            
            logging.setLogRecordFactory(record_factory)
        
        self.logger.log(level, msg, **kwargs)
        
        # 恢复原始 factory
        if extra:
            logging.setLogRecordFactory(logging._logRecordFactory)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, exc_info=True, **kwargs)
    
    def log_data(self, level: str, msg: str, data: dict):
        """记录带结构化数据的日志"""
        self._log(getattr(logging, level.upper()), msg, extra={'data': data})


# 全局日志器缓存
_loggers: Dict[str, Logger] = {}


def get_logger(name: str, config: dict = None) -> Logger:
    """获取或创建日志器"""
    if name not in _loggers:
        _loggers[name] = Logger(name, config)
    return _loggers[name]


def configure_logging(config_path: str):
    """从配置文件配置日志系统"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    logging_config = config.get('logging', {})
    
    # 更新根日志器配置
    root_logger = get_logger('root', logging_config)
    return root_logger


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 示例：使用日志系统
    logger = get_logger(__name__)
    
    logger.debug("这是调试信息")
    logger.info("这是信息")
    logger.warning("这是警告")
    logger.error("这是错误")
    logger.critical("这是严重错误")
    
    # 记录异常
    try:
        1 / 0
    except Exception:
        logger.exception("发生除零错误")
    
    # 记录结构化数据
    logger.log_data("INFO", "用户操作", {
        "user_id": 12345,
        "action": "login",
        "ip": "192.168.1.1"
    })
