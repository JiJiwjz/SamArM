#!/usr/bin/env python3
"""
钉钉机器人通知模块
"""

import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class DingTalkNotifier:
    """钉钉机器人通知器"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        """
        初始化钉钉通知器
        
        Args:
            webhook_url: 钉钉机器人 webhook 地址，如果不提供则从环境变量读取
        """
        self.webhook_url = webhook_url or os.getenv("DINGTALK_WEBHOOK")
        self.enabled = os.getenv("DINGTALK_ENABLED", "true").lower() == "true"
        
        if not self.webhook_url and self.enabled:
            logger.warning("未配置 DINGTALK_WEBHOOK，钉钉通知将被禁用")
            self.enabled = False
    
    def send_text(self, content: str, at_all: bool = False) -> bool:
        """
        发送文本消息
        
        Args:
            content: 消息内容
            at_all: 是否 @ 所有人
            
        Returns:
            是否发送成功
        """
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            data = {
                "msgtype": "text",
                "text": {
                    "content": content
                },
                "at": {
                    "isAtAll": at_all
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"✅ 钉钉消息发送成功")
                return True
            else:
                logger.error(f"❌ 钉钉消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 钉钉消息发送异常: {e}")
            return False
    
    def send_markdown(self, title: str, text: str) -> bool:
        """
        发送 Markdown 消息
        
        Args:
            title: 消息标题
            text: Markdown 格式的消息内容
            
        Returns:
            是否发送成功
        """
        if not self.enabled or not self.webhook_url:
            return False
        
        try:
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": text
                }
            }
            
            response = requests.post(
                self.webhook_url,
                json=data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            result = response.json()
            if result.get("errcode") == 0:
                logger.info(f"✅ 钉钉 Markdown 消息发送成功")
                return True
            else:
                logger.error(f"❌ 钉钉 Markdown 消息发送失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 钉钉 Markdown 消息发送异常: {e}")
            return False
    
    def send_job_start(self, days_back: int, top_n: int) -> bool:
        """发送任务启动通知"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""📊 Arxiv 论文日报任务已启动

⏰ 启动时间: {now}
📅 回溯天数: {days_back} 天
📝 计划发送: Top {top_n} 篇

正在执行中...
"""
        return self.send_text(content)
    
    def send_job_complete(self, stats: Dict[str, Any], execution_time: float) -> bool:
        """
        发送任务完成通知
        
        Args:
            stats: 运行统计信息
            execution_time: 执行耗时（秒）
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取关键统计信息
        crawled = stats.get('crawled', 0)
        filtered = stats.get('filtered', 0)
        new_papers = stats.get('new_papers', 0)
        sent = stats.get('sent', 0)
        send_result = stats.get('send_result', '未知')
        
        # 构建 Markdown 消息
        title = "✅ Arxiv 论文日报任务完成"
        text = f"""## {title}

### 📊 运行统计
- **完成时间**: {now}
- **执行耗时**: {execution_time:.1f} 秒

### 📈 论文数据
- **爬取论文**: {crawled} 篇
- **筛选后**: {filtered} 篇
- **新论文**: {new_papers} 篇
- **发送数量**: {sent} 篇

### 📧 邮件状态
- **发送结果**: {send_result}

---
*SamArM 自动论文日报系统*
"""
        return self.send_markdown(title, text)
    
    def send_job_error(self, error_msg: str) -> bool:
        """发送任务错误通知"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""❌ Arxiv 论文日报任务执行失败

⏰ 时间: {now}
🚨 错误信息:
{error_msg}

请检查服务器日志！
"""
        return self.send_text(content, at_all=False)


# 便捷函数
def get_notifier() -> DingTalkNotifier:
    """获取钉钉通知器实例"""
    return DingTalkNotifier()
