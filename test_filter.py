#!/usr/bin/env python3
"""
测试过滤和分类模块
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import ArxivCrawler
from src.config import ConfigManager
from src.filter import PaperFilter, Deduplicator

def main():
    """测试完整流程：爬取 -> 去重 -> 分类筛选"""
    
    print("\n" + "="*70)
    print("🚀 论文爬取 -> 去重 -> 分类筛选 完整测试")
    print("="*70 + "\n")
    
    # ===== 第1步：爬取论文 =====
    print("📥 第1步：从arxiv爬取论文...")
    print("-" * 70)
    
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    crawler = ArxivCrawler(arxiv_config)
    papers = crawler.fetch_papers(days_back=3)
    papers_dict = [p.to_dict() for p in papers]
    
    print(f"✅ 成功爬取 {len(papers_dict)} 篇论文\n")
    
    # ===== 第2步：去重 =====
    print("🔄 第2步：论文去重...")
    print("-" * 70)
    
    deduplicator = Deduplicator()
    unique_papers, duplicate_papers = deduplicator.deduplicate_papers(papers_dict)
    
    print(f"✅ 去重完成:")
    print(f"   新增论文: {len(unique_papers)}")
    print(f"   重复论文: {len(duplicate_papers)}\n")
    
    if duplicate_papers:
        print("   重复论文列表:")
        for paper in duplicate_papers[:3]:
            print(f"   - {paper['title'][:60]}... (重复于: {paper['duplicate_of']})")
        if len(duplicate_papers) > 3:
            print(f"   ... 还有 {len(duplicate_papers) - 3} 篇\n")
    
    # ===== 第3步：分类和筛选 =====
    print("🏷️  第3步：论文分类与相关性评分...")
    print("-" * 70)
    
    filter_obj = PaperFilter(min_relevance_score=0.0)
    filtered_papers, rejected = filter_obj.filter_and_rank(unique_papers, sort_by='relevance_score')
    
    print(f"✅ 筛选完成:")
    print(f"   通过筛选: {len(filtered_papers)}")
    print(f"   被过滤: {len(rejected)}\n")
    
    # ===== 第4步：统计分析 =====
    print("📊 第4步：统计分析...")
    print("-" * 70)
    
    stats = filter_obj.get_statistics(filtered_papers)
    
    print(f"总论文数: {stats['total']}")
    print(f"平均相关性分数: {stats['avg_relevance_score']:.3f}")
    print(f"\n按主题分布:")
    for topic, count in sorted(stats['topics'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {topic}: {count}")
    
    print(f"\n高频关键词 Top 15:")
    keywords_sorted = sorted(stats['keywords_frequency'].items(), key=lambda x: x[1], reverse=True)
    for keyword, freq in keywords_sorted[:15]:
        print(f"  {keyword}: {freq}")
    
    # ===== 第5步：详细展示 =====
    print("\n" + "="*70)
    print("📚 相关性最高的10篇论文")
    print("="*70 + "\n")
    
    for i, paper in enumerate(filtered_papers[:10], 1):
        print(f"【论文 {i}】")
        print(f"标题: {paper.title}")
        print(f"作者: {', '.join(paper.authors[:3])}...")
        print(f"发布时间: {paper.published[:10]}")
        print(f"主题分类: {paper.topic_category} (相关性: {paper.relevance_score:.3f})")
        print(f"匹配关键词: {', '.join(paper.matched_keywords[:5])}")
        if len(paper.matched_keywords) > 5:
            print(f"            ... 还有 {len(paper.matched_keywords) - 5} 个关键词")
        print(f"链接: {paper.arxiv_url}\n")
    
    # ===== 按主题分组展示 =====
    print("="*70)
    print("🗂️  按主题分组展示")
    print("="*70 + "\n")
    
    grouped = filter_obj.group_by_topic(filtered_papers)
    
    for topic in sorted(grouped.keys()):
        papers_in_topic = grouped[topic]
        print(f"【{topic}】({len(papers_in_topic)}篇)")
        for paper in papers_in_topic[:3]:
            print(f"  - {paper.title[:70]}")
        if len(papers_in_topic) > 3:
            print(f"  ... 还有 {len(papers_in_topic) - 3} 篇")
        print()
    
    print("="*70)
    print("✅ 测试完成！")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
