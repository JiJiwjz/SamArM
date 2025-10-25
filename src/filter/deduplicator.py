"""
论文去重模块
基于标题、作者、DOI进行去重
"""

import json
import os
import logging
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class PaperFingerprint:
    """论文指纹 - 用于去重"""
    paper_id: str
    title_hash: str          # 标题哈希
    authors_hash: str        # 作者哈希
    doi: str                 # DOI
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'paper_id': self.paper_id,
            'title_hash': self.title_hash,
            'authors_hash': self.authors_hash,
            'doi': self.doi
        }


class Deduplicator:
    """论文去重器"""
    
    def __init__(self, cache_file: str = 'data/processed_papers.json'):
        """
        初始化去重器
        
        Args:
            cache_file: 已处理论文缓存文件路径
        """
        self.cache_file = cache_file
        self.processed_papers: Set[str] = set()  # 存储论文哈希值
        self.paper_records: Dict[str, Dict] = {}  # 存储完整记录
        
        self._load_cache()
    
    def _load_cache(self):
        """从缓存文件加载已处理论文"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.paper_records = data.get('records', {})
                    # 提取所有论文哈希值
                    self.processed_papers = set(self.paper_records.keys())
                    logger.info(f"从缓存加载了 {len(self.processed_papers)} 条论文记录")
            except Exception as e:
                logger.warning(f"加载缓存文件失败: {e}")
        else:
            logger.info("缓存文件不存在，开始新建")
    
    def _save_cache(self):
        """保存缓存到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'records': self.paper_records,
                    'updated_at': datetime.utcnow().isoformat(),
                    'total_count': len(self.paper_records)
                }, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"缓存已保存到 {self.cache_file}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    @staticmethod
    def _compute_title_hash(title: str) -> str:
        """
        计算标题哈希值
        标准化处理：小写、去除特殊字符、去除多余空格
        
        Args:
            title: 论文标题
        
        Returns:
            标题哈希值
        """
        # 标准化标题
        normalized = title.lower().strip()
        # 只保留字母、数字和空格
        normalized = ''.join(c if c.isalnum() or c.isspace() else '' for c in normalized)
        # 去除多余空格
        normalized = ' '.join(normalized.split())
        
        # 计算SHA256哈希
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    @staticmethod
    def _compute_authors_hash(authors: List[str], top_n: int = 3) -> str:
        """
        计算作者哈希值
        只使用前N个作者，降低作者顺序变化的影响
        
        Args:
            authors: 作者列表
            top_n: 使用前N个作者
        
        Returns:
            作者哈希值
        """
        # 只取前N个作者
        top_authors = authors[:top_n]
        # 标准化：小写、去除空格
        authors_str = '|'.join([a.lower().strip() for a in top_authors])
        
        return hashlib.sha256(authors_str.encode()).hexdigest()
    
    def get_paper_fingerprint(self, paper: Dict) -> PaperFingerprint:
        """
        生成论文指纹
        
        Args:
            paper: 论文信息字典
        
        Returns:
            论文指纹对象
        """
        title_hash = self._compute_title_hash(paper.get('title', ''))
        authors_hash = self._compute_authors_hash(paper.get('authors', []))
        doi = paper.get('doi', '')
        
        fingerprint = PaperFingerprint(
            paper_id=paper.get('paper_id', ''),
            title_hash=title_hash,
            authors_hash=authors_hash,
            doi=doi
        )
        
        return fingerprint
    
    def _generate_duplicate_key(self, fingerprint: PaperFingerprint) -> str:
        """
        生成重复检测的唯一键
        组合标题和作者哈希
        
        Args:
            fingerprint: 论文指纹
        
        Returns:
            唯一键
        """
        key = f"{fingerprint.title_hash}_{fingerprint.authors_hash}"
        return key
    
    def is_duplicate(self, paper: Dict) -> Tuple[bool, str]:
        """
        检查论文是否重复
        
        Args:
            paper: 论文信息字典
        
        Returns:
            (是否重复, 如果重复则返回第一次出现的paper_id，否则返回空字符串)
        """
        fingerprint = self.get_paper_fingerprint(paper)
        dup_key = self._generate_duplicate_key(fingerprint)
        
        if dup_key in self.processed_papers:
            # 查找第一次出现的paper_id
            if dup_key in self.paper_records:
                first_paper_id = self.paper_records[dup_key].get('paper_id', 'unknown')
                logger.debug(f"检测到重复论文: {paper['title'][:50]}... (第一次出现: {first_paper_id})")
                return True, first_paper_id
            return True, ''
        
        return False, ''
    
    def mark_as_processed(self, paper: Dict) -> bool:
        """
        将论文标记为已处理
        
        Args:
            paper: 论文信息字典
        
        Returns:
            是否成功标记（如果已存在则返回False）
        """
        fingerprint = self.get_paper_fingerprint(paper)
        dup_key = self._generate_duplicate_key(fingerprint)
        
        if dup_key in self.processed_papers:
            logger.debug(f"论文已存在: {paper['title'][:50]}...")
            return False
        
        # 记录论文信息
        self.paper_records[dup_key] = {
            'paper_id': paper.get('paper_id', ''),
            'title': paper.get('title', ''),
            'authors': paper.get('authors', []),
            'marked_at': datetime.utcnow().isoformat(),
            'fingerprint': fingerprint.to_dict()
        }
        
        self.processed_papers.add(dup_key)
        self._save_cache()
        
        logger.debug(f"已标记论文: {paper['title'][:50]}...")
        return True
    
    def deduplicate_papers(self, papers: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        对论文列表进行去重
        
        Args:
            papers: 论文列表
        
        Returns:
            (去重后的论文列表, 重复论文列表)
        """
        unique_papers = []
        duplicate_papers = []
        
        for paper in papers:
            is_dup, first_paper_id = self.is_duplicate(paper)
            
            if is_dup:
                paper['duplicate_of'] = first_paper_id
                duplicate_papers.append(paper)
            else:
                unique_papers.append(paper)
                self.mark_as_processed(paper)
        
        logger.info(f"去重完成: 新增{len(unique_papers)}篇, 重复{len(duplicate_papers)}篇")
        return unique_papers, duplicate_papers
    
    def clear_cache(self):
        """清空缓存"""
        self.processed_papers.clear()
        self.paper_records.clear()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        logger.info("缓存已清空")


if __name__ == '__main__':
    # 测试去重功能
    dedup = Deduplicator()
    
    # 测试论文
    test_papers = [
        {
            'paper_id': '2510.20820v1',
            'title': 'LayerComposer: Interactive Personalized T2I via Spatially-Aware Layered Canvas',
            'authors': ['Guocheng Gordon Qian', 'Ruihang Zhang', 'Tsai-Shien Chen']
        },
        {
            'paper_id': '2510.20820v2',
            'title': 'LayerComposer: Interactive Personalized T2I via Spatially-Aware Layered Canvas',  # 重复
            'authors': ['Guocheng Gordon Qian', 'Ruihang Zhang', 'Tsai-Shien Chen']
        },
        {
            'paper_id': '2510.20819v1',
            'title': 'Towards General Modality Translation with Contrastive Learning',
            'authors': ['Nimrod Berman', 'Omkar Joglekar']
        }
    ]
    
    unique, duplicates = dedup.deduplicate_papers(test_papers)
    
    print(f"\n✅ 唯一论文: {len(unique)}")
    for p in unique:
        print(f"  - {p['title'][:50]}")
    
    print(f"\n❌ 重复论文: {len(duplicates)}")
    for p in duplicates:
        print(f"  - {p['title'][:50]} (重复于: {p['duplicate_of']})")
