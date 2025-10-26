#!/usr/bin/env python3
"""通知模块"""

from .dingtalk import DingTalkNotifier, get_notifier

__all__ = ['DingTalkNotifier', 'get_notifier']
