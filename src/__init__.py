"""
Arxiv Mailbot - 自动化获取arxiv论文并邮件推送
"""

__version__ = '0.1.0'
__author__ = 'Samxander'

from .config import ConfigManager, config_manager
from .crawler import ArxivCrawler, Paper

__all__ = [
    'ConfigManager',
    'config_manager',
    'ArxivCrawler',
    'Paper',
]
