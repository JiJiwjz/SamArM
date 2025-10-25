"""
论文过滤模块
包含去重、分类、相关性评分功能
"""

from .deduplicator import Deduplicator, PaperFingerprint
from .paper_filter import PaperFilter, PaperClassifier, FilteredPaper

__all__ = [
    'Deduplicator',
    'PaperFingerprint',
    'PaperFilter',
    'PaperClassifier',
    'FilteredPaper',
]
