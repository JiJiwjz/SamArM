#!/usr/bin/env python3
"""
测试爬虫脚本
从项目根目录运行此脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import ArxivCrawler
from src.config import ConfigManager

def main():
    """测试爬虫"""
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    print(f"\n📄 arxiv爬虫配置:")
    print(f"  关键词: {arxiv_config.get('keywords')}")
    print(f"  分类: {arxiv_config.get('categories')}")
    print(f"  最大结果数: {arxiv_config.get('max_results')}")
    
    # 创建爬虫实例
    print("\n🚀 开始爬取论文...")
    crawler = ArxivCrawler(arxiv_config)
    
    # 获取论文
    papers = crawler.fetch_papers(days_back=7)
    
    # 显示结果
    print(f"\n✅ 成功获取 {len(papers)} 篇论文\n")
    for i, paper in enumerate(papers[:5], 1):
        print(f"【论文 {i}】")
        print(f"标题: {paper.title}")
        print(f"作者: {', '.join(paper.authors[:3])}...")
        print(f"发布时间: {paper.published}")
        print(f"链接: {paper.arxiv_url}")
        print(f"摘要预览: {paper.summary[:150]}...\n")


if __name__ == '__main__':
    main()
