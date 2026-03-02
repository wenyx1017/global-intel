#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度系统 - Cron 调度器
Scheduler - Cron-based Task Scheduler

支持：
- YAML 配置调度任务
- 动态添加/删除任务
- 任务执行日志
- 失败重试机制
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from croniter import croniter
import threading
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.logger import get_logger


class SchedulerTask:
    """调度任务类"""
    
    def __init__(self, name: str, cron_expr: str, handler: Callable, 
                 args: tuple = (), kwargs: dict = None):
        self.name = name
        self.cron_expr = cron_expr
        self.handler = handler
        self.args = args
        self.kwargs = kwargs or {}
        self.enabled = True
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.fail_count = 0
        self.max_retries = 3
        self.retry_delay = 60  # 秒
        
        self._update_next_run()
    
    def _update_next_run(self):
        """计算下次运行时间"""
        if not self.enabled:
            self.next_run = None
            return
        
        try:
            cron = croniter(self.cron_expr, datetime.now())
            self.next_run = cron.get_next(datetime)
        except Exception as e:
            logger.error(f"任务 {self.name} cron 表达式解析失败：{e}")
            self.next_run = None
    
    def should_run(self) -> bool:
        """检查是否应该运行"""
        if not self.enabled or self.next_run is None:
            return False
        return datetime.now() >= self.next_run
    
    def execute(self):
        """执行任务"""
        try:
            logger.info(f"执行任务：{self.name}")
            self.handler(*self.args, **self.kwargs)
            self.last_run = datetime.now()
            self.run_count += 1
            self.fail_count = 0
            self._update_next_run()
            logger.info(f"任务 {self.name} 执行成功")
        except Exception as e:
            logger.error(f"任务 {self.name} 执行失败：{e}")
            self.fail_count += 1
            
            # 重试逻辑
            if self.fail_count < self.max_retries:
                logger.warning(f"任务 {self.name} 将在 {self.retry_delay}秒后重试 ({self.fail_count}/{self.max_retries})")
                # 简单重试：延迟下次运行时间
                from datetime import timedelta
                self.next_run = datetime.now() + timedelta(seconds=self.retry_delay)
            else:
                logger.error(f"任务 {self.name} 重试次数耗尽，已禁用")
                self.enabled = False
    
    def reset(self):
        """重置任务状态"""
        self.enabled = True
        self.fail_count = 0
        self._update_next_run()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "cron_expr": self.cron_expr,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "fail_count": self.fail_count
        }


class Scheduler:
    """调度器主类"""
    
    def __init__(self, config_path: str = None):
        self.tasks: Dict[str, SchedulerTask] = {}
        self.running = False
        self._thread = None
        self._lock = threading.Lock()
        
        # 加载配置
        if config_path:
            self.load_config(config_path)
        
        logger.info("调度器初始化完成")
    
    def load_config(self, config_path: str):
        """从 YAML 配置加载调度任务"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            schedule_config = config.get('schedule', {})
            
            # 加载采集层任务
            collectors = schedule_config.get('collectors', {})
            for name, cron_expr in collectors.items():
                self.add_task(f"collector_{name}", cron_expr, self._default_handler)
            
            # 加载处理层任务
            processors = schedule_config.get('processors', {})
            for name, cron_expr in processors.items():
                self.add_task(f"processor_{name}", cron_expr, self._default_handler)
            
            # 加载服务层任务
            services = schedule_config.get('services', {})
            for name, cron_expr in services.items():
                self.add_task(f"service_{name}", cron_expr, self._default_handler)
            
            logger.info(f"从配置加载了 {len(self.tasks)} 个调度任务")
            
        except Exception as e:
            logger.error(f"加载调度配置失败：{e}")
            raise
    
    def _default_handler(self, *args, **kwargs):
        """默认处理器（实际使用时应替换为具体逻辑）"""
        logger.info(f"执行默认处理器：{args}, {kwargs}")
    
    def add_task(self, name: str, cron_expr: str, handler: Callable, 
                 args: tuple = (), kwargs: dict = None):
        """添加调度任务"""
        with self._lock:
            task = SchedulerTask(name, cron_expr, handler, args, kwargs)
            self.tasks[name] = task
            logger.info(f"添加任务：{name} (cron: {cron_expr})")
    
    def remove_task(self, name: str):
        """移除调度任务"""
        with self._lock:
            if name in self.tasks:
                del self.tasks[name]
                logger.info(f"移除任务：{name}")
            else:
                logger.warning(f"任务不存在：{name}")
    
    def enable_task(self, name: str):
        """启用任务"""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].reset()
                logger.info(f"启用任务：{name}")
            else:
                logger.warning(f"任务不存在：{name}")
    
    def disable_task(self, name: str):
        """禁用任务"""
        with self._lock:
            if name in self.tasks:
                self.tasks[name].enabled = False
                self.tasks[name].next_run = None
                logger.info(f"禁用任务：{name}")
            else:
                logger.warning(f"任务不存在：{name}")
    
    def get_task_status(self, name: str = None) -> dict:
        """获取任务状态"""
        with self._lock:
            if name:
                if name in self.tasks:
                    return self.tasks[name].to_dict()
                return None
            
            # 返回所有任务状态
            return {name: task.to_dict() for name, task in self.tasks.items()}
    
    def _run_loop(self):
        """调度器运行循环"""
        logger.info("调度器启动")
        
        while self.running:
            try:
                # 检查所有任务
                with self._lock:
                    tasks_to_run = [task for task in self.tasks.values() if task.should_run()]
                
                # 执行需要运行的任务
                for task in tasks_to_run:
                    # 在新线程中执行，避免阻塞
                    thread = threading.Thread(target=task.execute, daemon=True)
                    thread.start()
                
                # 每秒检查一次
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"调度器循环错误：{e}")
                time.sleep(5)
        
        logger.info("调度器停止")
    
    def start(self, blocking: bool = False):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行中")
            return
        
        self.running = True
        
        if blocking:
            self._run_loop()
        else:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("调度器在后台启动")
    
    def stop(self):
        """停止调度器"""
        logger.info("停止调度器...")
        self.running = False
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        logger.info("调度器已停止")
    
    def run_now(self, name: str):
        """立即运行指定任务"""
        with self._lock:
            if name in self.tasks:
                thread = threading.Thread(target=self.tasks[name].execute, daemon=True)
                thread.start()
                logger.info(f"立即执行任务：{name}")
            else:
                logger.warning(f"任务不存在：{name}")


# 全局日志器
logger = get_logger(__name__)


# ==================== 使用示例 ====================
if __name__ == "__main__":
    # 示例：创建调度器
    config_path = os.path.join(os.path.dirname(__file__), "../config.yaml")
    
    scheduler = Scheduler(config_path)
    
    # 添加自定义任务
    def sample_task(name: str):
        logger.info(f"执行示例任务：{name}")
        time.sleep(1)
    
    scheduler.add_task("sample_task", "*/10 * * * *", sample_task, args=("test",))
    
    # 启动调度器
    try:
        scheduler.start(blocking=True)
    except KeyboardInterrupt:
        scheduler.stop()
