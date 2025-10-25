"""
论文主题分类与筛选模块
负责对论文进行关键词匹配、相关性评分和分类
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
import json

logger = logging.getLogger(__name__)


@dataclass
class FilteredPaper:
    """筛选后的论文 - 包含分类和相关性信息"""
    paper_id: str
    title: str
    authors: List[str]
    summary: str
    published: str
    updated: str
    categories: str
    pdf_url: str
    arxiv_url: str
    fetch_time: str
    
    # 筛选相关字段
    relevance_score: float              # 相关性分数 0-1
    matched_keywords: List[str]         # 匹配的关键词
    topic_category: str                 # 论文主题分类
    classification_details: Dict        # 分类详情
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class PaperClassifier:
    """论文分类器 - 对论文进行主题分类"""
    
    # 主题分类配置
    TOPIC_KEYWORDS = {
        'image_denoising': {
            'keywords': ['denoise', 'denoising', 'noise removal', 'image quality', 'restoration'],
            'weight': 1.0,
            'description': '图像去噪'
        },
        'image_deraining': {
            'keywords': ['derain', 'deraining', 'rain removal', 'raindrop', 'weather'],
            'weight': 1.0,
            'description': '图像去雨'
        },
        'reinforcement_learning': {
            'keywords': ['reinforcement learning', 'RL', 'Q-learning', 'policy gradient', 'reward', 'agent', 'environment'],
            'weight': 1.0,
            'description': '强化学习'
        },
        'embodied_ai': {
            'keywords': ['embodied', 'embodied AI', 'robot', 'navigation', 'vision-language-action', 'VLA', 'embodied agent'],
            'weight': 1.0,
            'description': '具身智能'
        },
        'computer_vision': {
            'keywords': ['vision', 'image', 'visual', 'video', 'detection', 'segmentation', 'recognition'],
            'weight': 0.5,
            'description': '计算机视觉'
        },
        'deep_learning': {
            'keywords': ['deep learning', 'neural network', 'CNN', 'transformer', 'model', 'network'],
            'weight': 0.3,
            'description': '深度学习'
        }
    }
    
    def __init__(self):
        """初始化分类器"""
        logger.info(f"论文分类器已初始化，包含{len(self.TOPIC_KEYWORDS)}个主题")
    
    def classify_paper(self, paper: Dict) -> Tuple[str, Dict, float]:
        """
        对单篇论文进行分类
        
        Args:
            paper: 论文信息字典
        
        Returns:
            (主要主题, 分类详情, 综合得分)
        """
        title = paper.get('title', '').lower()
        summary = paper.get('summary', '').lower()
        
        # 组合文本
        full_text = f"{title}. {summary}"
        
        # 计算每个主题的得分
        topic_scores = {}
        for topic, config in self.TOPIC_KEYWORDS.items():
            score = self._calculate_topic_score(full_text, config)
            topic_scores[topic] = score
        
        # 查找最高分主题
        main_topic = max(topic_scores, key=topic_scores.get)
        max_score = topic_scores[main_topic]
        
        # 分类详情
        classification_details = {
            'main_topic': main_topic,
            'topic_scores': topic_scores,
            'max_score': max_score,
            'description': self.TOPIC_KEYWORDS.get(main_topic, {}).get('description', '')
        }
        
        return main_topic, classification_details, max_score
    
    def _calculate_topic_score(self, text: str, config: Dict) -> float:
        """
        计算文本对某个主题的匹配得分
        
        Args:
            text: 待分析文本
            config: 主题配置
        
        Returns:
            得分 0-1
        """
        keywords = config.get('keywords', [])
        weight = config.get('weight', 1.0)
        
        if not keywords:
            return 0.0
        
        # 统计匹配的关键词
        matched_count = 0
        for keyword in keywords:
            # 使用词边界匹配，避免部分匹配
            pattern = rf'\b{re.escape(keyword.lower())}\b'
            if re.search(pattern, text):
                matched_count += 1
        
        # 计算得分：(匹配数 / 总关键词数) * 权重
        score = (matched_count / len(keywords)) * weight
        
        # 限制在0-1之间
        return min(score, 1.0)
    
    def get_matched_keywords(self, paper: Dict) -> List[str]:
        """
        获取论文匹配的所有关键词
        
        Args:
            paper: 论文信息字典
        
        Returns:
            匹配的关键词列表
        """
        title = paper.get('title', '').lower()
        summary = paper.get('summary', '').lower()
        full_text = f"{title}. {summary}"
        
        matched = []
        for topic, config in self.TOPIC_KEYWORDS.items():
            for keyword in config.get('keywords', []):
                pattern = rf'\b{re.escape(keyword.lower())}\b'
                if re.search(pattern, full_text):
                    matched.append(keyword)
        
        return list(set(matched))  # 去重


class PaperFilter:
    """论文筛选器 - 综合去重、分类、相关性评分"""
    
    def __init__(self, min_relevance_score: float = 0.0):
        """
        初始化筛选器
        
        Args:
            min_relevance_score: 最低相关性分数（0-1）
        """
        self.classifier = PaperClassifier()
        self.min_relevance_score = min_relevance_score
        logger.info(f"论文筛选器已初始化，最低相关性分数: {min_relevance_score}")
    
    def filter_papers(self, papers: List[Dict]) -> Tuple[List[FilteredPaper], List[Dict]]:
        """
        对论文列表进行筛选
        
        Args:
            papers: 原始论文列表
        
        Returns:
            (筛选后的论文列表, 被过滤的论文及原因)
        """
        filtered_papers = []
        rejected_papers = []
        
        for paper in papers:
            # 进行分类和相关性评分
            main_topic, details, score = self.classifier.classify_paper(paper)
            
            # 检查是否满足最低相关性要求
            if score < self.min_relevance_score:
                rejected_papers.append({
                    'paper': paper,
                    'reason': f'相关性分数过低: {score:.2f} < {self.min_relevance_score}'
                })
                continue
            
            # 获取匹配的关键词
            matched_keywords = self.classifier.get_matched_keywords(paper)
            
            # 创建筛选后的论文对象
            filtered_paper = FilteredPaper(
                paper_id=paper.get('paper_id', ''),
                title=paper.get('title', ''),
                authors=paper.get('authors', []),
                summary=paper.get('summary', ''),
                published=paper.get('published', ''),
                updated=paper.get('updated', ''),
                categories=paper.get('categories', ''),
                pdf_url=paper.get('pdf_url', ''),
                arxiv_url=paper.get('arxiv_url', ''),
                fetch_time=paper.get('fetch_time', ''),
                
                relevance_score=score,
                matched_keywords=matched_keywords,
                topic_category=main_topic,
                classification_details=details
            )
            
            filtered_papers.append(filtered_paper)
        
        logger.info(f"筛选完成: 通过{len(filtered_papers)}篇, 被过滤{len(rejected_papers)}篇")
        return filtered_papers, rejected_papers
    
    def filter_and_rank(self, papers: List[Dict], sort_by: str = 'relevance_score') ->  Tuple[List[FilteredPaper], List[Dict]]:
        """
        对论文进行筛选和排序
        
        Args:
            papers: 论文列表
            sort_by: 排序方式 ('relevance_score'|'published'|'topic_category')
        
        Returns:
            排序后的筛选论文列表
        """
        filtered_papers, rejected = self.filter_papers(papers)
        
        # 排序
        if sort_by == 'relevance_score':
            filtered_papers.sort(key=lambda p: p.relevance_score, reverse=True)
        elif sort_by == 'published':
            filtered_papers.sort(key=lambda p: p.published, reverse=True)
        elif sort_by == 'topic_category':
            filtered_papers.sort(key=lambda p: p.topic_category)
        
        return filtered_papers, rejected
    
    def group_by_topic(self, papers: List[FilteredPaper]) -> Dict[str, List[FilteredPaper]]:
        """
        按主题对论文进行分组
        
        Args:
            papers: 筛选后的论文列表
        
        Returns:
            按主题分组的论文字典
        """
        grouped = {}
        
        for paper in papers:
            topic = paper.topic_category
            if topic not in grouped:
                grouped[topic] = []
            grouped[topic].append(paper)
        
        return grouped
    
    def get_statistics(self, papers: List[FilteredPaper]) -> Dict:
        """
        获取筛选后论文的统计信息
        
        Args:
            papers: 筛选后的论文列表
        
        Returns:
            统计信息字典
        """
        if not papers:
            return {
                'total': 0,
                'avg_relevance_score': 0.0,
                'topics': {},
                'keywords_frequency': {}
            }
        
        # 按主题统计
        topics = {}
        keywords_freq = {}
        total_score = 0.0
        
        for paper in papers:
            topic = paper.topic_category
            topics[topic] = topics.get(topic, 0) + 1
            
            total_score += paper.relevance_score
            
            for keyword in paper.matched_keywords:
                keywords_freq[keyword] = keywords_freq.get(keyword, 0) + 1
        
        return {
            'total': len(papers),
            'avg_relevance_score': total_score / len(papers),
            'topics': topics,
            'keywords_frequency': keywords_freq
        }


def main():
    """测试筛选功能"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.crawler import ArxivCrawler
    from src.config import ConfigManager
    
    # 获取配置和论文
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    crawler = ArxivCrawler(arxiv_config)
    papers = crawler.fetch_papers(days_back=3)
    
    # 转换为字典列表
    papers_dict = [p.to_dict() for p in papers]
    
    # 创建筛选器
    filter_obj = PaperFilter(min_relevance_score=0.0)
    
    # 筛选论文
    filtered_papers, rejected = filter_obj.filter_and_rank(papers_dict, sort_by='relevance_score')
    
    print(f"\n✅ 筛选完成: {len(filtered_papers)} 篇论文通过")
    print(f"❌ 被过滤: {len(rejected)} 篇论文\n")
    
    # 显示统计信息
    stats = filter_obj.get_statistics(filtered_papers)
    print(f"📊 统计信息:")
    print(f"  总数: {stats['total']}")
    print(f"  平均相关性分数: {stats['avg_relevance_score']:.2f}")
    print(f"  按主题分布: {stats['topics']}")
    print(f"  高频关键词: {dict(sorted(stats['keywords_frequency'].items(), key=lambda x: x[1], reverse=True)[:10])}\n")
    
    # 显示前5篇高相关性论文
    print("📚 相关性最高的5篇论文:")
    for i, paper in enumerate(filtered_papers[:5], 1):
        print(f"\n{i}. {paper.title}")
        print(f"   主题: {paper.topic_category} (相关性: {paper.relevance_score:.2f})")
        print(f"   匹配关键词: {', '.join(paper.matched_keywords[:5])}")


if __name__ == '__main__':
    main()
