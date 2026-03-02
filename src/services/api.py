#!/usr/bin/env python3
"""
REST API 服务
基于 FastAPI 提供报告、订阅、推送的 HTTP 接口
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Body
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field


# 导入服务模块
from report import ReportGenerator, Report
from subscribe import SubscriptionManager, Subscriber, UserPreference
from notifier import Notifier, NotificationMessage, DeliveryResult


# ==================== Pydantic 模型 ====================

class UserCreate(BaseModel):
    """创建用户请求"""
    user_id: str = Field(..., description="用户唯一 ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    discord_id: Optional[str] = Field(None, description="Discord 用户 ID")


class UserUpdate(BaseModel):
    """更新用户请求"""
    username: Optional[str] = Field(None, description="用户名")
    email: Optional[str] = Field(None, description="邮箱地址")
    discord_id: Optional[str] = Field(None, description="Discord 用户 ID")
    is_active: Optional[bool] = Field(None, description="是否活跃")


class SubscriptionRequest(BaseModel):
    """订阅请求"""
    subscription_type: str = Field(..., description="订阅类型 (daily/weekly/realtime)")


class NotificationRequest(BaseModel):
    """通知请求"""
    title: str = Field(..., description="标题")
    content: str = Field(..., description="内容")
    priority: str = Field("normal", description="优先级 (high/normal/low)")
    channel: str = Field("discord", description="推送渠道 (discord/email)")
    recipient: str = Field(..., description="接收者")


class ReportGenerateRequest(BaseModel):
    """报告生成请求"""
    report_type: str = Field("daily", description="报告类型 (daily/weekly)")
    date: Optional[str] = Field(None, description="报告日期 (YYYY-MM-DD)")


class BroadcastRequest(BaseModel):
    """批量推送请求"""
    title: str
    content: str
    priority: str = "normal"
    recipients: List[Dict[str, str]] = Field(
        ..., 
        description="接收者列表，每项包含 channel 和 recipient"
    )


# ==================== 全局服务实例 ====================

report_generator: Optional[ReportGenerator] = None
subscription_manager: Optional[SubscriptionManager] = None
notifier: Optional[Notifier] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global report_generator, subscription_manager, notifier
    
    # 启动时初始化
    report_generator = ReportGenerator()
    subscription_manager = SubscriptionManager()
    notifier = Notifier()
    
    yield
    
    # 关闭时清理（如果需要）
    pass


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="情报服务 API",
    description="提供报告生成、订阅管理、推送服务的 REST API 接口",
    version="1.0.0",
    lifespan=lifespan
)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 健康检查 ====================

@app.get("/", tags=["健康检查"])
async def root():
    """API 根路径"""
    return {
        "service": "情报服务 API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "report": report_generator is not None,
            "subscription": subscription_manager is not None,
            "notifier": notifier is not None
        }
    }


# ==================== 报告 API ====================

@app.post("/reports/generate", tags=["报告"], response_model=Dict)
async def generate_report(request: ReportGenerateRequest):
    """
    生成报告
    
    - **report_type**: 报告类型 (daily/weekly)
    - **date**: 可选，报告日期 (YYYY-MM-DD)，默认为今天
    """
    try:
        if request.report_type == "daily":
            date = None
            if request.date:
                date = datetime.strptime(request.date, '%Y-%m-%d')
            
            report = report_generator.generate_daily_report(date)
        elif request.report_type == "weekly":
            end_date = None
            if request.date:
                end_date = datetime.strptime(request.date, '%Y-%m-%d')
            
            report = report_generator.generate_weekly_report(end_date)
        else:
            raise HTTPException(status_code=400, detail="不支持的报告类型")
        
        return {
            "success": True,
            "report_id": report.report_id,
            "title": report.title,
            "type": report.report_type,
            "generated_at": report.generated_at
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reports", tags=["报告"], response_model=List[str])
async def list_reports(report_type: Optional[str] = Query(None, description="报告类型过滤")):
    """列出所有报告"""
    return report_generator.list_reports(report_type)


@app.get("/reports/{report_id}", tags=["报告"], response_model=Dict)
async def get_report(report_id: str):
    """获取指定报告"""
    report = report_generator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    return report.to_dict()


@app.get("/reports/{report_id}/download", tags=["报告"])
async def download_report(report_id: str, format: str = Query("json", description="格式 (json/txt)")):
    """下载报告文件"""
    reports_dir = report_generator.data_dir / "reports"
    
    if format == "json":
        filepath = reports_dir / f"{report_id}.json"
    elif format == "txt":
        filepath = reports_dir / f"{report_id}.txt"
    else:
        raise HTTPException(status_code=400, detail="不支持的格式")
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    media_type = "application/json" if format == "json" else "text/plain"
    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filepath.name}"
        }
    )


# ==================== 订阅 API ====================

@app.post("/users", tags=["订阅管理"], response_model=Dict)
async def create_user(user: UserCreate):
    """创建新用户"""
    try:
        subscriber = subscription_manager.add_user(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            discord_id=user.discord_id
        )
        
        return {
            "success": True,
            "user_id": subscriber.user_id,
            "username": subscriber.username,
            "created_at": subscriber.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users", tags=["订阅管理"], response_model=List[Dict])
async def list_users(active_only: bool = Query(True, description="是否只列出活跃用户")):
    """列出所有用户"""
    users = subscription_manager.list_users(active_only)
    return [u.to_dict() for u in users]


@app.get("/users/{user_id}", tags=["订阅管理"], response_model=Dict)
async def get_user(user_id: str):
    """获取用户信息"""
    user = subscription_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return user.to_dict()


@app.put("/users/{user_id}", tags=["订阅管理"], response_model=Dict)
async def update_user(user_id: str, user_update: UserUpdate):
    """更新用户信息"""
    update_data = user_update.dict(exclude_unset=True)
    
    if not update_data:
        raise HTTPException(status_code=400, detail="没有要更新的字段")
    
    user = subscription_manager.update_user(user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "user_id": user.user_id,
        "updated_at": user.updated_at
    }


@app.delete("/users/{user_id}", tags=["订阅管理"], response_model=Dict)
async def delete_user(user_id: str, hard_delete: bool = Query(False, description="是否硬删除")):
    """
    删除用户
    
    - **hard_delete**: False 为停用，True 为彻底删除
    """
    if hard_delete:
        success = subscription_manager.delete_user(user_id)
    else:
        success = subscription_manager.deactivate_user(user_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {"success": True, "action": "deleted" if hard_delete else "deactivated"}


@app.post("/users/{user_id}/subscribe", tags=["订阅管理"], response_model=Dict)
async def subscribe_user(user_id: str, request: SubscriptionRequest):
    """用户订阅某类报告"""
    success = subscription_manager.subscribe(user_id, request.subscription_type)
    
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "user_id": user_id,
        "subscription_type": request.subscription_type
    }


@app.delete("/users/{user_id}/unsubscribe", tags=["订阅管理"], response_model=Dict)
async def unsubscribe_user(user_id: str, subscription_type: str = Query(..., description="订阅类型")):
    """用户取消订阅"""
    success = subscription_manager.unsubscribe(user_id, subscription_type)
    
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "user_id": user_id,
        "subscription_type": subscription_type
    }


@app.get("/users/{user_id}/subscriptions", tags=["订阅管理"], response_model=List[str])
async def get_user_subscriptions(user_id: str):
    """获取用户的订阅列表"""
    user = subscription_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return subscription_manager.get_user_subscriptions(user_id)


@app.get("/subscriptions/{subscription_type}", tags=["订阅管理"], response_model=List[Dict])
async def get_subscribers(subscription_type: str):
    """获取某类订阅的所有用户"""
    subscribers = subscription_manager.get_subscribers(subscription_type)
    return [s.to_dict() for s in subscribers]


@app.get("/stats", tags=["订阅管理"], response_model=Dict)
async def get_stats():
    """获取订阅统计信息"""
    return subscription_manager.get_stats()


# ==================== 推送 API ====================

@app.post("/notify", tags=["推送服务"], response_model=Dict)
async def send_notification(request: NotificationRequest, background_tasks: BackgroundTasks):
    """
    发送通知
    
    - **title**: 通知标题
    - **content**: 通知内容
    - **priority**: 优先级 (high/normal/low)
    - **channel**: 推送渠道 (discord/email)
    - **recipient**: 接收者（Discord 频道 ID 或邮箱地址）
    """
    message = NotificationMessage(
        title=request.title,
        content=request.content,
        priority=request.priority
    )
    
    try:
        if request.channel.lower() == 'discord':
            result = await notifier.send_discord(
                message,
                channel_id=request.recipient
            )
        elif request.channel.lower() == 'email':
            result = notifier.send_email(
                message,
                to_address=request.recipient
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的推送渠道")
        
        return {
            "success": result.success,
            "channel": result.channel,
            "recipient": result.recipient,
            "message_id": result.message_id,
            "error": result.error,
            "timestamp": result.timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notify/broadcast", tags=["推送服务"], response_model=Dict)
async def broadcast_notification(request: BroadcastRequest, 
                                background_tasks: BackgroundTasks):
    """
    批量推送通知
    
    - **title**: 通知标题
    - **content**: 通知内容
    - **priority**: 优先级
    - **recipients**: 接收者列表，每项包含 channel 和 recipient
    """
    message = NotificationMessage(
        title=request.title,
        content=request.content,
        priority=request.priority
    )
    
    try:
        results = await notifier.broadcast(message, request.recipients)
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        return {
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": [asdict(r) for r in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reports/{report_id}/send", tags=["推送服务", "报告"], response_model=Dict)
async def send_report(report_id: str, 
                     recipients: List[Dict[str, str]] = Body(..., description="接收者列表"),
                     background_tasks: BackgroundTasks = None):
    """
    发送报告给指定接收者
    
    - **report_id**: 报告 ID
    - **recipients**: 接收者列表，每项包含 channel 和 recipient
    """
    report = report_generator.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    try:
        results = notifier.send_report(report.to_dict(), recipients)
        
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        return {
            "success": True,
            "report_id": report_id,
            "total": len(results),
            "successful": successful,
            "failed": failed
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notify/stats", tags=["推送服务"], response_model=Dict)
async def get_delivery_stats(hours: int = Query(24, description="统计最近多少小时")):
    """获取推送统计"""
    return notifier.get_delivery_stats(hours)


# ==================== 模板管理 API ====================

@app.get("/templates", tags=["模板管理"], response_model=List[str])
async def list_templates():
    """列出所有报告模板"""
    templates_dir = report_generator.templates_dir
    if not templates_dir.exists():
        return []
    
    return [f.name for f in templates_dir.glob("*.txt")]


@app.get("/templates/{template_name}", tags=["模板管理"], response_model=str)
async def get_template(template_name: str):
    """获取模板内容"""
    template_path = report_generator.templates_dir / template_name
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="模板不存在")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


@app.put("/templates/{template_name}", tags=["模板管理"], response_model=Dict)
async def save_template(template_name: str, content: str = Body(..., description="模板内容")):
    """保存模板"""
    template_path = report_generator.templates_dir / template_name
    
    with open(template_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return {
        "success": True,
        "template_name": template_name,
        "path": str(template_path)
    }


@app.delete("/templates/{template_name}", tags=["模板管理"], response_model=Dict)
async def delete_template(template_name: str):
    """删除模板"""
    template_path = report_generator.templates_dir / template_name
    
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="模板不存在")
    
    template_path.unlink()
    
    return {
        "success": True,
        "template_name": template_name
    }


# ==================== 数据导入导出 API ====================

@app.post("/users/export", tags=["数据管理"], response_model=Dict)
async def export_users():
    """导出用户数据"""
    import tempfile
    
    fd, filepath = tempfile.mkstemp(suffix='.json', prefix='users_export_')
    
    try:
        count = subscription_manager.export_users(filepath)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    finally:
        os.unlink(filepath)


@app.post("/users/import", tags=["数据管理"], response_model=Dict)
async def import_users(merge: bool = Query(False, description="是否合并现有数据"),
                      file_content: Dict = Body(..., description="用户数据 JSON")):
    """导入用户数据"""
    import tempfile
    import json
    
    fd, filepath = tempfile.mkstemp(suffix='.json', prefix='users_import_')
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(file_content, f, ensure_ascii=False, indent=2)
        
        count = subscription_manager.import_users(filepath, merge)
        
        return {
            "success": True,
            "imported_count": count,
            "merge": merge
        }
    finally:
        os.unlink(filepath)


# ==================== 错误处理 ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": str(exc),
            "status_code": 500
        }
    )


# ==================== 启动命令 ====================

if __name__ == "__main__":
    import uvicorn
    
    print("启动情报服务 API...")
    print("API 文档：http://localhost:8000/docs")
    print("健康检查：http://localhost:8000/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
