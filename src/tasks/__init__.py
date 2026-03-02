"""
任务注册中心 - 硬编码任务
"""

from src.tasks.announcement_crawler import main as announcement_crawler_main

# 任务注册表
TASKS = {
    # 专项任务
    'announcement_crawler': {
        'handler': announcement_crawler_main,
        'description': '上市公司公告爬取（硬编码）',
        'timeout': 300,  # 5 分钟
    },
}

def get_task(task_name: str):
    """获取任务处理器"""
    task = TASKS.get(task_name)
    if not task:
        raise ValueError(f"未知任务：{task_name}")
    return task

def list_tasks():
    """列出所有任务"""
    return list(TASKS.keys())
