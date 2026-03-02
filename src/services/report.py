#!/usr/bin/env python3
"""
情报报告生成服务
支持每日/每周报告生成，从数据源聚合信息并格式化输出
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass
class ReportSection:
    """报告章节"""
    title: str
    content: str
    priority: str = "normal"  # high, normal, low
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class Report:
    """报告数据结构"""
    report_id: str
    report_type: str  # daily, weekly
    generated_at: str
    period_start: str
    period_end: str
    title: str
    summary: str
    sections: List[ReportSection]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return {
            'report_id': self.report_id,
            'report_type': self.report_type,
            'generated_at': self.generated_at,
            'period_start': self.period_start,
            'period_end': self.period_end,
            'title': self.title,
            'summary': self.summary,
            'sections': [asdict(s) for s in self.sections],
            'metadata': self.metadata
        }


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        初始化报告生成器
        
        Args:
            templates_dir: 模板目录路径，默认为当前目录的 templates/
        """
        if templates_dir is None:
            templates_dir = Path(__file__).parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Jinja2 环境
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(['html', 'xml', 'txt'])
        )
        
        # 数据源目录
        self.data_dir = Path(__file__).parent.parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(self, date: Optional[datetime] = None) -> Report:
        """
        生成每日报告
        
        Args:
            date: 报告日期，默认为今天
            
        Returns:
            Report 对象
        """
        if date is None:
            date = datetime.now()
        
        report_id = f"daily_{date.strftime('%Y%m%d')}"
        
        # 收集当日数据
        sections = self._collect_daily_data(date)
        
        # 生成摘要
        summary = self._generate_summary(sections)
        
        report = Report(
            report_id=report_id,
            report_type="daily",
            generated_at=datetime.now().isoformat(),
            period_start=date.strftime('%Y-%m-%d 00:00:00'),
            period_end=date.strftime('%Y-%m-%d 23:59:59'),
            title=f"每日情报报告 - {date.strftime('%Y年%m月%d日')}",
            summary=summary,
            sections=sections,
            metadata={
                'date': date.strftime('%Y-%m-%d'),
                'total_sections': len(sections)
            }
        )
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def generate_weekly_report(self, end_date: Optional[datetime] = None) -> Report:
        """
        生成每周报告
        
        Args:
            end_date: 报告结束日期，默认为今天
            
        Returns:
            Report 对象
        """
        if end_date is None:
            end_date = datetime.now()
        
        # 计算周一日期
        start_date = end_date - timedelta(days=end_date.weekday())
        
        report_id = f"weekly_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
        
        # 收集本周数据
        sections = self._collect_weekly_data(start_date, end_date)
        
        # 生成摘要
        summary = self._generate_summary(sections)
        
        report = Report(
            report_id=report_id,
            report_type="weekly",
            generated_at=datetime.now().isoformat(),
            period_start=start_date.strftime('%Y-%m-%d 00:00:00'),
            period_end=end_date.strftime('%Y-%m-%d 23:59:59'),
            title=f"每周情报报告 - {start_date.strftime('%m月%d日')}至{end_date.strftime('%m月%d日')}",
            summary=summary,
            sections=sections,
            metadata={
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'total_sections': len(sections)
            }
        )
        
        # 保存报告
        self._save_report(report)
        
        return report
    
    def _collect_daily_data(self, date: datetime) -> List[ReportSection]:
        """收集每日数据，生成报告章节"""
        sections = []
        
        # 示例：从数据文件读取
        # 实际使用时替换为真实数据源
        market_data = self._load_market_data(date)
        if market_data:
            sections.append(ReportSection(
                title="市场动态",
                content=market_data,
                priority="high",
                tags=["市场", "行情"]
            ))
        
        news_data = self._load_news_data(date)
        if news_data:
            sections.append(ReportSection(
                title="重要新闻",
                content=news_data,
                priority="normal",
                tags=["新闻", "公告"]
            ))
        
        # 如果没有数据，生成默认章节
        if not sections:
            sections.append(ReportSection(
                title="今日概览",
                content=f"{date.strftime('%Y年%m月%d日')}暂无特别数据。",
                priority="low",
                tags=["概览"]
            ))
        
        return sections
    
    def _collect_weekly_data(self, start_date: datetime, end_date: datetime) -> List[ReportSection]:
        """收集每周数据，生成报告章节"""
        sections = []
        
        # 周统计
        sections.append(ReportSection(
            title="本周总结",
            content=f"从{start_date.strftime('%m月%d日')}到{end_date.strftime('%m月%d日')}的情报汇总。",
            priority="high",
            tags=["周度", "总结"]
        ))
        
        # 趋势分析
        sections.append(ReportSection(
            title="趋势分析",
            content="本周市场趋势分析内容。",
            priority="normal",
            tags=["趋势", "分析"]
        ))
        
        return sections
    
    def _load_market_data(self, date: datetime) -> Optional[str]:
        """加载市场数据"""
        data_file = self.data_dir / f"market_{date.strftime('%Y%m%d')}.json"
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False, indent=2)
        return None
    
    def _load_news_data(self, date: datetime) -> Optional[str]:
        """加载新闻数据"""
        data_file = self.data_dir / f"news_{date.strftime('%Y%m%d')}.json"
        if data_file.exists():
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, ensure_ascii=False, indent=2)
        return None
    
    def _generate_summary(self, sections: List[ReportSection]) -> str:
        """生成报告摘要"""
        high_priority = [s for s in sections if s.priority == "high"]
        if high_priority:
            return f"本报告包含{len(sections)}个章节，其中{len(high_priority)}个高优先级内容。"
        return f"本报告包含{len(sections)}个章节。"
    
    def _save_report(self, report: Report):
        """保存报告到文件"""
        reports_dir = self.data_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存 JSON 格式
        json_file = reports_dir / f"{report.report_id}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 生成格式化报告（如果有模板）
        try:
            template = self.env.get_template(f"{report.report_type}_report.txt")
            rendered = template.render(report=report)
            
            txt_file = reports_dir / f"{report.report_id}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(rendered)
        except Exception:
            # 模板不存在时使用默认格式
            txt_file = reports_dir / f"{report.report_id}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(self._format_report_default(report))
    
    def _format_report_default(self, report: Report) -> str:
        """默认报告格式化"""
        lines = [
            "=" * 60,
            report.title,
            "=" * 60,
            f"生成时间：{report.generated_at}",
            f"报告周期：{report.period_start} 至 {report.period_end}",
            "",
            "摘要:",
            report.summary,
            "",
            "-" * 60,
        ]
        
        for section in report.sections:
            lines.extend([
                f"\n【{section.title}】",
                f"优先级：{section.priority}",
                f"标签：{', '.join(section.tags)}",
                "",
                section.content,
                ""
            ])
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def get_report(self, report_id: str) -> Optional[Report]:
        """根据 ID 获取报告"""
        reports_dir = self.data_dir / "reports"
        json_file = reports_dir / f"{report_id}.json"
        
        if not json_file.exists():
            return None
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        sections = [ReportSection(**s) for s in data['sections']]
        return Report(
            report_id=data['report_id'],
            report_type=data['report_type'],
            generated_at=data['generated_at'],
            period_start=data['period_start'],
            period_end=data['period_end'],
            title=data['title'],
            summary=data['summary'],
            sections=sections,
            metadata=data.get('metadata')
        )
    
    def list_reports(self, report_type: Optional[str] = None) -> List[str]:
        """
        列出所有报告
        
        Args:
            report_type: 可选，过滤报告类型 (daily/weekly)
            
        Returns:
            报告 ID 列表
        """
        reports_dir = self.data_dir / "reports"
        if not reports_dir.exists():
            return []
        
        report_ids = []
        for f in reports_dir.glob("*.json"):
            report_id = f.stem
            if report_type is None or report_id.startswith(report_type):
                report_ids.append(report_id)
        
        return sorted(report_ids, reverse=True)


# 便捷函数
def generate_daily(date: Optional[datetime] = None) -> Report:
    """生成每日报告"""
    generator = ReportGenerator()
    return generator.generate_daily_report(date)


def generate_weekly(end_date: Optional[datetime] = None) -> Report:
    """生成每周报告"""
    generator = ReportGenerator()
    return generator.generate_weekly_report(end_date)


if __name__ == "__main__":
    # 测试代码
    print("生成每日报告...")
    daily = generate_daily()
    print(f"报告 ID: {daily.report_id}")
    print(f"标题：{daily.title}")
    print(f"章节数：{len(daily.sections)}")
    
    print("\n生成每周报告...")
    weekly = generate_weekly()
    print(f"报告 ID: {weekly.report_id}")
    print(f"标题：{weekly.title}")
    print(f"章节数：{len(weekly.sections)}")
