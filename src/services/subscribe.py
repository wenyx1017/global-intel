#!/usr/bin/env python3
"""
订阅管理系统
用户订阅管理、偏好设置、订阅状态跟踪
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import hashlib


class SubscriptionType(Enum):
    """订阅类型"""
    DAILY = "daily"
    WEEKLY = "weekly"
    REALTIME = "realtime"
    CUSTOM = "custom"


class DeliveryChannel(Enum):
    """推送渠道"""
    DISCORD = "discord"
    EMAIL = "email"
    BOTH = "both"


@dataclass
class UserPreference:
    """用户偏好设置"""
    report_types: List[str] = field(default_factory=lambda: ["daily"])
    delivery_channel: str = "discord"
    delivery_time: str = "09:00"  # 24 小时制
    timezone: str = "Asia/Shanghai"
    language: str = "zh-CN"
    filters: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserPreference':
        return cls(**data)


@dataclass
class Subscriber:
    """订阅用户"""
    user_id: str
    username: str
    email: Optional[str] = None
    discord_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    is_active: bool = True
    preferences: UserPreference = None
    
    def __post_init__(self):
        if self.preferences is None:
            self.preferences = UserPreference()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'discord_id': self.discord_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active,
            'preferences': self.preferences.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Subscriber':
        data['preferences'] = UserPreference.from_dict(data.get('preferences', {}))
        return cls(**data)


class SubscriptionManager:
    """订阅管理器"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        初始化订阅管理器
        
        Args:
            data_dir: 数据目录，默认为 services 目录下的 subscribers/
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "subscribers"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self.subscriptions_file = self.data_dir / "subscriptions.json"
        
        # 加载数据
        self._load_data()
    
    def _load_data(self):
        """加载用户和订阅数据"""
        # 加载用户
        self.users: Dict[str, Subscriber] = {}
        if self.users_file.exists():
            with open(self.users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.users = {uid: Subscriber.from_dict(u) for uid, u in data.items()}
        
        # 加载订阅关系
        self.subscriptions: Dict[str, Set[str]] = {}  # subscription_type -> set of user_ids
        if self.subscriptions_file.exists():
            with open(self.subscriptions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.subscriptions = {k: set(v) for k, v in data.items()}
    
    def _save_data(self):
        """保存用户和订阅数据"""
        # 保存用户
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uid: u.to_dict() for uid, u in self.users.items()},
                f, ensure_ascii=False, indent=2
            )
        
        # 保存订阅关系
        with open(self.subscriptions_file, 'w', encoding='utf-8') as f:
            json.dump(
                {k: list(v) for k, v in self.subscriptions.items()},
                f, ensure_ascii=False, indent=2
            )
    
    def add_user(self, user_id: str, username: str, 
                 email: Optional[str] = None,
                 discord_id: Optional[str] = None,
                 preferences: Optional[UserPreference] = None) -> Subscriber:
        """
        添加新用户
        
        Args:
            user_id: 用户唯一 ID
            username: 用户名
            email: 邮箱地址（可选）
            discord_id: Discord 用户 ID（可选）
            preferences: 用户偏好（可选，使用默认值）
            
        Returns:
            创建的 Subscriber 对象
        """
        if user_id in self.users:
            raise ValueError(f"用户 {user_id} 已存在")
        
        subscriber = Subscriber(
            user_id=user_id,
            username=username,
            email=email,
            discord_id=discord_id,
            preferences=preferences
        )
        
        self.users[user_id] = subscriber
        self._save_data()
        
        return subscriber
    
    def get_user(self, user_id: str) -> Optional[Subscriber]:
        """获取用户信息"""
        return self.users.get(user_id)
    
    def update_user(self, user_id: str, **kwargs) -> Optional[Subscriber]:
        """
        更新用户信息
        
        Args:
            user_id: 用户 ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的 Subscriber 对象，如果用户不存在返回 None
        """
        if user_id not in self.users:
            return None
        
        user = self.users[user_id]
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.now().isoformat()
        self._save_data()
        
        return user
    
    def deactivate_user(self, user_id: str) -> bool:
        """
        停用用户（不删除数据）
        
        Returns:
            是否成功停用
        """
        if user_id not in self.users:
            return False
        
        user = self.users[user_id]
        user.is_active = False
        user.updated_at = datetime.now().isoformat()
        
        # 从所有订阅中移除
        for sub_type in self.subscriptions:
            self.subscriptions[sub_type].discard(user_id)
        
        self._save_data()
        return True
    
    def delete_user(self, user_id: str) -> bool:
        """
        删除用户
        
        Returns:
            是否成功删除
        """
        if user_id not in self.users:
            return False
        
        del self.users[user_id]
        
        # 从所有订阅中移除
        for sub_type in self.subscriptions:
            self.subscriptions[sub_type].discard(user_id)
        
        self._save_data()
        return True
    
    def subscribe(self, user_id: str, subscription_type: str) -> bool:
        """
        用户订阅某类报告
        
        Args:
            user_id: 用户 ID
            subscription_type: 订阅类型 (daily/weekly/realtime/custom)
            
        Returns:
            是否成功订阅
        """
        if user_id not in self.users:
            return False
        
        if subscription_type not in self.subscriptions:
            self.subscriptions[subscription_type] = set()
        
        self.subscriptions[subscription_type].add(user_id)
        
        # 更新用户偏好
        user = self.users[user_id]
        if subscription_type not in user.preferences.report_types:
            user.preferences.report_types.append(subscription_type)
            user.updated_at = datetime.now().isoformat()
        
        self._save_data()
        return True
    
    def unsubscribe(self, user_id: str, subscription_type: str) -> bool:
        """
        用户取消订阅
        
        Args:
            user_id: 用户 ID
            subscription_type: 订阅类型
            
        Returns:
            是否成功取消订阅
        """
        if user_id not in self.users:
            return False
        
        if subscription_type in self.subscriptions:
            self.subscriptions[subscription_type].discard(user_id)
        
        # 更新用户偏好
        user = self.users[user_id]
        if subscription_type in user.preferences.report_types:
            user.preferences.report_types.remove(subscription_type)
            user.updated_at = datetime.now().isoformat()
        
        self._save_data()
        return True
    
    def get_subscribers(self, subscription_type: str) -> List[Subscriber]:
        """
        获取某类订阅的所有用户
        
        Args:
            subscription_type: 订阅类型
            
        Returns:
            订阅用户列表
        """
        user_ids = self.subscriptions.get(subscription_type, set())
        return [
            self.users[uid] 
            for uid in user_ids 
            if uid in self.users and self.users[uid].is_active
        ]
    
    def get_user_subscriptions(self, user_id: str) -> List[str]:
        """
        获取用户的所有订阅
        
        Args:
            user_id: 用户 ID
            
        Returns:
            订阅类型列表
        """
        if user_id not in self.users:
            return []
        
        return [
            sub_type 
            for sub_type, users in self.subscriptions.items() 
            if user_id in users
        ]
    
    def list_users(self, active_only: bool = True) -> List[Subscriber]:
        """
        列出所有用户
        
        Args:
            active_only: 是否只列出活跃用户
            
        Returns:
            用户列表
        """
        if active_only:
            return [u for u in self.users.values() if u.is_active]
        return list(self.users.values())
    
    def search_users(self, query: str) -> List[Subscriber]:
        """
        搜索用户
        
        Args:
            query: 搜索关键词（匹配用户名、邮箱、ID）
            
        Returns:
            匹配的用户列表
        """
        query = query.lower()
        return [
            user for user in self.users.values()
            if (query in user.user_id.lower() or
                query in user.username.lower() or
                (user.email and query in user.email.lower()) or
                (user.discord_id and query in user.discord_id.lower()))
        ]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取订阅统计信息"""
        stats = {
            'total_users': len(self.users),
            'active_users': sum(1 for u in self.users.values() if u.is_active),
            'subscriptions_by_type': {}
        }
        
        for sub_type, users in self.subscriptions.items():
            stats['subscriptions_by_type'][sub_type] = len(users)
        
        return stats
    
    def export_users(self, filepath: str) -> bool:
        """导出用户数据到文件"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(
                    {uid: u.to_dict() for uid, u in self.users.items()},
                    f, ensure_ascii=False, indent=2
                )
            return True
        except Exception:
            return False
    
    def import_users(self, filepath: str, merge: bool = False) -> int:
        """
        从文件导入用户数据
        
        Args:
            filepath: 导入文件路径
            merge: 是否合并（False 则覆盖）
            
        Returns:
            导入的用户数量
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not merge:
            self.users = {}
            self.subscriptions = {}
        
        count = 0
        for uid, user_data in data.items():
            user = Subscriber.from_dict(user_data)
            self.users[uid] = user
            
            # 重建订阅关系
            for sub_type in user.preferences.report_types:
                if sub_type not in self.subscriptions:
                    self.subscriptions[sub_type] = set()
                self.subscriptions[sub_type].add(uid)
            
            count += 1
        
        self._save_data()
        return count


# 便捷函数
def create_user(user_id: str, username: str, **kwargs) -> Subscriber:
    """创建新用户"""
    manager = SubscriptionManager()
    return manager.add_user(user_id, username, **kwargs)


def get_user(user_id: str) -> Optional[Subscriber]:
    """获取用户"""
    manager = SubscriptionManager()
    return manager.get_user(user_id)


def subscribe_user(user_id: str, sub_type: str) -> bool:
    """用户订阅"""
    manager = SubscriptionManager()
    return manager.subscribe(user_id, sub_type)


if __name__ == "__main__":
    # 测试代码
    print("初始化订阅管理器...")
    manager = SubscriptionManager()
    
    print("\n添加测试用户...")
    user = manager.add_user(
        user_id="test001",
        username="测试用户",
        email="test@example.com",
        discord_id="123456789"
    )
    print(f"用户：{user.username} ({user.user_id})")
    
    print("\n订阅每日报告...")
    manager.subscribe("test001", "daily")
    print(f"订阅类型：{manager.get_user_subscriptions('test001')}")
    
    print("\n获取每日报告订阅者...")
    subscribers = manager.get_subscribers("daily")
    print(f"订阅者数量：{len(subscribers)}")
    
    print("\n统计信息:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
