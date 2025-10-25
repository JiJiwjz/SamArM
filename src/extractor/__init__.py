"""
论文思想提取模块
负责调用AI API对论文进行核心思想提取
"""

from .deepseek_client import DeepSeekClient, DeepSeekBatchProcessor
from .idea_extractor import IdeaExtractor, ExtractedIdea

__all__ = [
    'DeepSeekClient',
    'DeepSeekBatchProcessor',
    'IdeaExtractor',
    'ExtractedIdea',
]
