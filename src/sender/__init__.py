"""
邮件发送模块
负责将论文摘要格式化并发送邮件
"""

from .email_formatter import EmailFormatter
from .email_sender import EmailSender
from .email_templates import EmailTemplate

__all__ = [
    'EmailFormatter',
    'EmailSender',
    'EmailTemplate',
]
