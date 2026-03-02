#!/usr/bin/env python3
"""
上市公司公告爬取任务 - 硬编码版本
直接调用 cn_announcement 爬虫项目
"""

import os
import sys
import subprocess
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/wenyx/.openclaw/workspace/global-intel/logs/announcement.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 硬编码配置 ====================

# 爬取器路径
CRAWLER_PATH = '/home/wenyx/.openclaw/workspace/cn_announcement'
CRAWLER_BIN = os.path.join(CRAWLER_PATH, 'cn_ann')

# 输出目录
OUTPUT_DIR = '/home/wenyx/.openclaw/workspace/global-intel/data/announcements'

# 监控股票列表（硬编码）
MONITORED_STOCKS = [
    # 上交所
    {'code': '600000', 'name': '浦发银行', 'exchange': 'SH'},
    {'code': '601318', 'name': '中国平安', 'exchange': 'SH'},
    {'code': '600519', 'name': '贵州茅台', 'exchange': 'SH'},
    
    # 科创板
    {'code': '688712', 'name': '北芯生命', 'exchange': 'SHK'},
    
    # 深交所
    {'code': '000001', 'name': '平安银行', 'exchange': 'SZ'},
    {'code': '000858', 'name': '五 粮 液', 'exchange': 'SZ'},
    {'code': '300750', 'name': '宁德时代', 'exchange': 'SZ'},
]

# ===================================================

def ensure_directories():
    """确保输出目录存在"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'raw'), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, 'processed'), exist_ok=True)

def run_crawler():
    """运行公告爬虫"""
    logger.info("=" * 60)
    logger.info("开始执行公告爬取任务")
    logger.info("=" * 60)
    
    # 检查爬虫二进制文件
    if not os.path.exists(CRAWLER_BIN):
        logger.error(f"爬虫程序不存在：{CRAWLER_BIN}")
        logger.info("尝试编译爬虫...")
        try:
            subprocess.run(
                ['go', 'build', '-o', CRAWLER_BIN, '.'],
                cwd=CRAWLER_PATH,
                check=True,
                capture_output=True
            )
            logger.info("爬虫编译成功")
        except Exception as e:
            logger.error(f"爬虫编译失败：{e}")
            return False
    
    # 确保输出目录
    ensure_directories()
    
    # 运行爬虫
    logger.info(f"运行爬虫：{CRAWLER_BIN}")
    logger.info(f"监控股票：{len(MONITORED_STOCKS)} 只")
    
    try:
        # 设置环境变量
        env = os.environ.copy()
        env['OUTPUT_DIR'] = OUTPUT_DIR
        
        # 运行爬虫
        result = subprocess.run(
            [CRAWLER_BIN],
            cwd=CRAWLER_PATH,
            env=env,
            capture_output=True,
            timeout=300  # 5 分钟超时
        )
        
        # 处理输出
        if result.stdout:
            for line in result.stdout.decode('utf-8').split('\n'):
                if line.strip():
                    logger.info(line.strip())
        
        if result.stderr:
            for line in result.stderr.decode('utf-8').split('\n'):
                if line.strip():
                    logger.error(line.strip())
        
        if result.returncode == 0:
            logger.info("公告爬取任务完成")
            
            # 统计结果
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            raw_files = len([f for f in os.listdir(os.path.join(OUTPUT_DIR, 'raw')) if f.endswith('.json')])
            processed_files = len([f for f in os.listdir(os.path.join(OUTPUT_DIR, 'processed')) if f.endswith('.json')])
            
            logger.info(f"原始数据文件：{raw_files} 个")
            logger.info(f"处理后文件：{processed_files} 个")
            
            return True
        else:
            logger.error(f"爬虫执行失败，返回码：{result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("爬虫执行超时（5 分钟）")
        return False
    except Exception as e:
        logger.error(f"爬虫执行异常：{e}")
        return False

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info(f"公告爬取任务启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    success = run_crawler()
    
    if success:
        logger.info("任务执行成功")
    else:
        logger.error("任务执行失败")
    
    logger.info("=" * 60)

if __name__ == '__main__':
    main()
