"""
邮件格式化模块
负责将论文数据格式化为邮件内容
"""

import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

from .email_templates import EmailTemplate

logger = logging.getLogger(__name__)


class EmailFormatter:
    """邮件格式化器"""
    
    def __init__(self):
        """初始化邮件格式化器"""
        logger.info("邮件格式化器已初始化")
    
    @staticmethod
    def sort_papers_by_relevance(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按相关性分数排序论文
        
        Args:
            papers: 论文列表
        
        Returns:
            排序后的论文列表
        """
        return sorted(papers, key=lambda p: p.get('relevance_score', 0), reverse=True)
    
    @staticmethod
    def get_topic_statistics(papers: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        获取主题统计信息
        
        Args:
            papers: 论文列表
        
        Returns:
            主题统计字典
        """
        stats = {}
        for paper in papers:
            topic = paper.get('topic_category', 'unknown')
            stats[topic] = stats.get(topic, 0) + 1
        return stats
    
    def format_papers_to_html(self, papers: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        将论文列表格式化为HTML邮件内容
        
        Args:
            papers: 论文列表
        
        Returns:
            (HTML内容, 统计信息)
        """
        # 按相关性排序
        sorted_papers = self.sort_papers_by_relevance(papers)
        
        # 获取统计信息
        topic_stats = self.get_topic_statistics(sorted_papers)
        
        logger.info(f"开始格式化 {len(sorted_papers)} 篇论文为HTML邮件")
        
        # 生成HTML
        html = EmailTemplate.generate_email_html(sorted_papers, topic_stats)
        
        stats = {
            'total_papers': len(sorted_papers),
            'topic_stats': topic_stats,
            'avg_relevance_score': sum(p.get('relevance_score', 0) for p in sorted_papers) / len(sorted_papers) if sorted_papers else 0,
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"HTML邮件生成完成，统计: {stats}")
        
        return html, stats
    
    def generate_plain_text_email(self, papers: List[Dict[str, Any]]) -> str:
        """
        生成纯文本邮件（备选方案）
        
        Args:
            papers: 论文列表
        
        Returns:
            纯文本邮件内容
        """
        sorted_papers = self.sort_papers_by_relevance(papers)
        
        text = f"""
{'='*80}
                    🖼️ Image Restoration 论文日报
                    {datetime.utcnow().strftime('%Y年%m月%d日')}
{'='*80}

📊 统计信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总论文数: {len(sorted_papers)} 篇
平均相关性: {sum(p.get('relevance_score', 0) for p in sorted_papers) / len(sorted_papers) if sorted_papers else 0:.1%}

"""
        
        # 主题统计
        topic_stats = self.get_topic_statistics(sorted_papers)
        text += "主题分布: " + ", ".join([f"{topic}: {count}篇" for topic, count in sorted(topic_stats.items(), key=lambda x: x[1], reverse=True)]) + "\n\n"
        
        # 论文列表
        text += f"{'='*80}\n论文列表\n{'='*80}\n\n"
        
        for i, paper in enumerate(sorted_papers, 1):
            text += f"""
【论文 {i}】
────────────────────────────────────────────────────────────────────────────
标题: {paper.get('title', '未知')}
作者: {', '.join(paper.get('authors', [])[:3])}
发布: {paper.get('published', '')[:10]}
主题: {paper.get('topic_category', 'unknown')}
相关性: {paper.get('relevance_score', 0):.1%}

🤖 AI总结:
{paper.get('ai_summary', '无')}

🔗 链接: {paper.get('arxiv_url', '#')}

"""
        
        text += f"""
{'='*80}
此邮件由 SamArM 自动生成（Image Restoration 专题）
© 2025 SamArM. Automated Paper Digest
{'='*80}
"""
        
        return text


def test_email_formatter():
    """测试邮件格式化"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.crawler import ArxivCrawler
    from src.config import ConfigManager
    from src.filter import PaperFilter, Deduplicator
    
    # 获取测试数据
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    crawler = ArxivCrawler(arxiv_config)
    papers = crawler.fetch_papers(days_back=3)
    papers_dict = [p.to_dict() for p in papers]
    
    deduplicator = Deduplicator()
    unique_papers, _ = deduplicator.deduplicate_papers(papers_dict)
    
    filter_obj = PaperFilter()
    filtered_papers, _ = filter_obj.filter_papers(unique_papers)
    filtered_dict = [p.to_dict() for p in filtered_papers[:5]]
    
    # 测试格式化
    formatter = EmailFormatter()
    html, stats = formatter.format_papers_to_html(filtered_dict)
    
    print("✅ 邮件HTML格式化成功")
    print(f"📊 统计信息: {stats}")
    print(f"\n✅ 邮件纯文本格式化成功")
    text = formatter.generate_plain_text_email(filtered_dict)
    print(f"纯文本长度: {len(text)} 字符")


if __name__ == '__main__':
    test_email_formatter()
