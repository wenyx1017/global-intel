#!/usr/bin/env python3
"""
推送服务
支持 Discord 和邮件推送，处理报告分发和通知
"""

import json
import os
import smtplib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import asyncio


@dataclass
class NotificationMessage:
    """通知消息"""
    title: str
    content: str
    priority: str = "normal"  # high, normal, low
    attachments: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DeliveryResult:
    """推送结果"""
    success: bool
    channel: str
    recipient: str
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class Notifier:
    """推送服务"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化推送服务
        
        Args:
            config_file: 配置文件路径，默认为 notifier_config.json
        """
        if config_file is None:
            config_file = Path(__file__).parent / "notifier_config.json"
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
        # 推送历史
        self.history_file = Path(__file__).parent / "delivery_history.json"
        self.delivery_history: List[Dict] = self._load_history()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认配置
        return {
            'discord': {
                'enabled': True,
                'webhook_url': '',
                'bot_token': '',
                'default_channel': ''
            },
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_address': '',
                'use_tls': True
            },
            'retry': {
                'max_attempts': 3,
                'delay_seconds': 5
            }
        }
    
    def _save_config(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _load_history(self) -> List[Dict]:
        """加载推送历史"""
        if self.history_file.exists():
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_history(self):
        """保存推送历史"""
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.delivery_history, f, ensure_ascii=False, indent=2)
    
    def configure_discord(self, webhook_url: str = '', bot_token: str = '', 
                         default_channel: str = ''):
        """配置 Discord 推送"""
        self.config['discord']['webhook_url'] = webhook_url
        self.config['discord']['bot_token'] = bot_token
        self.config['discord']['default_channel'] = default_channel
        self.config['discord']['enabled'] = bool(webhook_url or bot_token)
        self._save_config()
    
    def configure_email(self, smtp_server: str, smtp_port: int,
                       username: str, password: str, from_address: str,
                       use_tls: bool = True):
        """配置邮件推送"""
        self.config['email'].update({
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'username': username,
            'password': password,
            'from_address': from_address,
            'use_tls': use_tls,
            'enabled': True
        })
        self._save_config()
    
    async def send_discord(self, message: Union[str, NotificationMessage],
                          channel_id: Optional[str] = None,
                          webhook_url: Optional[str] = None) -> DeliveryResult:
        """
        发送 Discord 消息
        
        Args:
            message: 消息内容或 NotificationMessage 对象
            channel_id: 频道 ID（可选，使用默认频道）
            webhook_url: Webhook URL（可选，使用配置的）
            
        Returns:
            DeliveryResult 对象
        """
        if not self.config['discord']['enabled']:
            return DeliveryResult(
                success=False,
                channel='discord',
                recipient=channel_id or 'default',
                error='Discord 推送未启用'
            )
        
        # 处理消息
        if isinstance(message, str):
            msg = NotificationMessage(title='', content=message)
        else:
            msg = message
        
        # 获取 Webhook URL
        url = webhook_url or self.config['discord'].get('webhook_url', '')
        
        if not url:
            # 尝试使用 bot token
            token = self.config['discord'].get('bot_token', '')
            if token:
                return await self._send_discord_bot(msg, channel_id, token)
            else:
                return DeliveryResult(
                    success=False,
                    channel='discord',
                    recipient=channel_id or 'default',
                    error='未配置 Discord Webhook URL 或 Bot Token'
                )
        
        # 准备 payload
        payload = {
            'content': msg.content,
            'embeds': []
        }
        
        if msg.title:
            payload['embeds'].append({
                'title': msg.title,
                'description': msg.content,
                'color': self._get_priority_color(msg.priority),
                'timestamp': datetime.now().isoformat()
            })
        
        # 发送请求
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status in [200, 204]:
                        result = DeliveryResult(
                            success=True,
                            channel='discord',
                            recipient=channel_id or 'default',
                            message_id=str(response.status)
                        )
                    else:
                        result = DeliveryResult(
                            success=False,
                            channel='discord',
                            recipient=channel_id or 'default',
                            error=f'HTTP {response.status}: {await response.text()}'
                        )
        except Exception as e:
            result = DeliveryResult(
                success=False,
                channel='discord',
                recipient=channel_id or 'default',
                error=str(e)
            )
        
        self._record_delivery(result)
        return result
    
    async def _send_discord_bot(self, message: NotificationMessage,
                               channel_id: str, token: str) -> DeliveryResult:
        """使用 Discord Bot 发送消息"""
        if not channel_id:
            channel_id = self.config['discord'].get('default_channel', '')
        
        if not channel_id:
            return DeliveryResult(
                success=False,
                channel='discord',
                recipient='unknown',
                error='未指定频道 ID 且无默认频道'
            )
        
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'content': message.content
        }
        
        if message.title:
            payload['embeds'] = [{
                'title': message.title,
                'description': message.content,
                'color': self._get_priority_color(message.priority)
            }]
        
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = DeliveryResult(
                            success=True,
                            channel='discord',
                            recipient=channel_id,
                            message_id=data.get('id', '')
                        )
                    else:
                        result = DeliveryResult(
                            success=False,
                            channel='discord',
                            recipient=channel_id,
                            error=f'HTTP {response.status}'
                        )
        except Exception as e:
            result = DeliveryResult(
                success=False,
                channel='discord',
                recipient=channel_id,
                error=str(e)
            )
        
        self._record_delivery(result)
        return result
    
    def send_email(self, message: Union[str, NotificationMessage],
                  to_address: str, subject: Optional[str] = None,
                  attachments: Optional[List[str]] = None) -> DeliveryResult:
        """
        发送邮件
        
        Args:
            message: 消息内容或 NotificationMessage 对象
            to_address: 收件人邮箱
            subject: 邮件主题（可选）
            attachments: 附件路径列表（可选）
            
        Returns:
            DeliveryResult 对象
        """
        if not self.config['email']['enabled']:
            return DeliveryResult(
                success=False,
                channel='email',
                recipient=to_address,
                error='邮件推送未启用'
            )
        
        # 处理消息
        if isinstance(message, str):
            msg = NotificationMessage(title=subject or '', content=message)
        else:
            msg = message
            if subject:
                msg.title = subject
        
        if not msg.title:
            msg.title = '情报报告'
        
        # 创建邮件
        email = MIMEMultipart()
        email['From'] = self.config['email']['from_address']
        email['To'] = to_address
        email['Subject'] = msg.title
        
        # 添加正文
        email.attach(MIMEText(msg.content, 'plain', 'utf-8'))
        
        # 添加附件
        if attachments is None:
            attachments = msg.attachments
        
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={os.path.basename(filepath)}'
                    )
                    email.attach(part)
        
        # 发送邮件
        try:
            server = smtplib.SMTP(
                self.config['email']['smtp_server'],
                self.config['email']['smtp_port']
            )
            
            if self.config['email']['use_tls']:
                server.starttls()
            
            server.login(
                self.config['email']['username'],
                self.config['email']['password']
            )
            
            server.sendmail(
                self.config['email']['from_address'],
                to_address,
                email.as_string()
            )
            
            server.quit()
            
            result = DeliveryResult(
                success=True,
                channel='email',
                recipient=to_address
            )
        except Exception as e:
            result = DeliveryResult(
                success=False,
                channel='email',
                recipient=to_address,
                error=str(e)
            )
        
        self._record_delivery(result)
        return result
    
    async def send(self, message: Union[str, NotificationMessage],
                  channel: str, recipient: str,
                  **kwargs) -> DeliveryResult:
        """
        通用发送接口
        
        Args:
            message: 消息内容
            channel: 推送渠道 (discord/email)
            recipient: 接收者（Discord 频道 ID 或邮箱地址）
            **kwargs: 额外参数
            
        Returns:
            DeliveryResult 对象
        """
        if channel.lower() == 'discord':
            return await self.send_discord(message, channel_id=recipient, **kwargs)
        elif channel.lower() == 'email':
            return self.send_email(message, to_address=recipient, **kwargs)
        else:
            return DeliveryResult(
                success=False,
                channel=channel,
                recipient=recipient,
                error=f'不支持的推送渠道：{channel}'
            )
    
    async def broadcast(self, message: Union[str, NotificationMessage],
                       recipients: List[Dict[str, str]],
                       retry: bool = True) -> List[DeliveryResult]:
        """
        批量推送
        
        Args:
            message: 消息内容
            recipients: 接收者列表，每项包含 {'channel': 'discord/email', 'recipient': 'id/address'}
            retry: 是否重试失败的推送
            
        Returns:
            DeliveryResult 列表
        """
        results = []
        failed = []
        
        for recipient in recipients:
            channel = recipient.get('channel', 'discord')
            addr = recipient.get('recipient', '')
            
            if not addr:
                continue
            
            result = await self.send(message, channel, addr)
            results.append(result)
            
            if not result.success and retry:
                failed.append({
                    'channel': channel,
                    'recipient': addr,
                    'message': message
                })
        
        # 重试失败的推送
        if retry and failed:
            max_attempts = self.config['retry']['max_attempts']
            delay = self.config['retry']['delay_seconds']
            
            for attempt in range(max_attempts):
                if not failed:
                    break
                
                await asyncio.sleep(delay)
                still_failed = []
                
                for item in failed:
                    result = await self.send(
                        item['message'],
                        item['channel'],
                        item['recipient']
                    )
                    results.append(result)
                    
                    if not result.success:
                        still_failed.append(item)
                
                failed = still_failed
        
        return results
    
    def send_report(self, report_data: Dict, subscribers: List[Dict],
                   template: str = 'default') -> List[DeliveryResult]:
        """
        发送报告给订阅者
        
        Args:
            report_data: 报告数据
            subscribers: 订阅者列表，每项包含 {'channel': 'discord/email', 'recipient': 'id/address'}
            template: 使用的模板名称
            
        Returns:
            DeliveryResult 列表
        """
        # 生成报告消息
        title = report_data.get('title', '情报报告')
        summary = report_data.get('summary', '')
        content = self._format_report(report_data, template)
        
        message = NotificationMessage(
            title=title,
            content=content,
            priority='high' if report_data.get('priority') == 'high' else 'normal',
            metadata={'report_id': report_data.get('report_id', '')}
        )
        
        # 异步发送
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.broadcast(message, subscribers)
        )
    
    def _format_report(self, report_data: Dict, template: str) -> str:
        """格式化报告内容"""
        lines = [
            f"📊 {report_data.get('title', '情报报告')}",
            "",
            f"📅 报告周期：{report_data.get('period_start', '')} 至 {report_data.get('period_end', '')}",
            "",
            "📝 摘要:",
            report_data.get('summary', '无摘要'),
            "",
            "-" * 40,
        ]
        
        # 添加章节
        sections = report_data.get('sections', [])
        for section in sections:
            lines.extend([
                f"\n📌 {section.get('title', '无标题')}",
                section.get('content', ''),
                ""
            ])
        
        lines.append("-" * 40)
        lines.append(f"生成时间：{report_data.get('generated_at', '')}")
        
        return "\n".join(lines)
    
    def _get_priority_color(self, priority: str) -> int:
        """获取优先级对应的颜色（Discord embed 颜色）"""
        colors = {
            'high': 0xFF0000,    # 红色
            'normal': 0x00FF00,  # 绿色
            'low': 0x0000FF      # 蓝色
        }
        return colors.get(priority, 0x00FF00)
    
    def _record_delivery(self, result: DeliveryResult):
        """记录推送历史"""
        self.delivery_history.append(asdict(result))
        
        # 只保留最近 1000 条
        if len(self.delivery_history) > 1000:
            self.delivery_history = self.delivery_history[-1000:]
        
        self._save_history()
    
    def get_delivery_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取推送统计
        
        Args:
            hours: 统计最近多少小时
            
        Returns:
            统计信息字典
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()
        
        recent = [
            r for r in self.delivery_history
            if r['timestamp'] > cutoff_str
        ]
        
        total = len(recent)
        successful = sum(1 for r in recent if r['success'])
        failed = total - successful
        
        by_channel = {}
        for r in recent:
            channel = r['channel']
            if channel not in by_channel:
                by_channel[channel] = {'total': 0, 'success': 0}
            by_channel[channel]['total'] += 1
            if r['success']:
                by_channel[channel]['success'] += 1
        
        return {
            'period_hours': hours,
            'total_deliveries': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'by_channel': by_channel
        }
    
    def clear_history(self, days: int = 30):
        """清理历史记录"""
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        self.delivery_history = [
            r for r in self.delivery_history
            if r['timestamp'] > cutoff_str
        ]
        
        self._save_history()


# 便捷函数
async def send_discord_message(content: str, **kwargs) -> DeliveryResult:
    """发送 Discord 消息"""
    notifier = Notifier()
    return await notifier.send_discord(content, **kwargs)


def send_email_message(content: str, to_address: str, **kwargs) -> DeliveryResult:
    """发送邮件"""
    notifier = Notifier()
    return notifier.send_email(content, to_address, **kwargs)


if __name__ == "__main__":
    # 测试代码
    print("初始化推送服务...")
    notifier = Notifier()
    
    print("\n配置统计:")
    print(f"  Discord 启用：{notifier.config['discord']['enabled']}")
    print(f"  邮件启用：{notifier.config['email']['enabled']}")
    
    print("\n推送历史统计 (最近 24 小时):")
    stats = notifier.get_delivery_stats(hours=24)
    for key, value in stats.items():
        print(f"  {key}: {value}")
