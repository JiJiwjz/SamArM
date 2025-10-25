#!/usr/bin/env python3
"""
测试论文思想提取模块
完整流程：爬取 -> 筛选 -> AI总结提取
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from datetime import datetime

from src.crawler import ArxivCrawler
from src.config import ConfigManager
from src.filter import PaperFilter, Deduplicator
from src.extractor import IdeaExtractor


async def main():
    """完整测试流程"""
    
    print("\n" + "="*80)
    print("🚀 完整流程测试：爬取 -> 去重 -> 筛选 -> AI总结")
    print("="*80 + "\n")
    
    # ===== 第1步：爬取论文 =====
    print("📥 第1步：从arxiv爬取论文...")
    print("-" * 80)
    
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    crawler = ArxivCrawler(arxiv_config)
    papers = crawler.fetch_papers(days_back=3)
    papers_dict = [p.to_dict() for p in papers]
    
    print(f"✅ 成功爬取 {len(papers_dict)} 篇论文\n")
    
    # ===== 第2步：去重 =====
    print("🔄 第2步：论文去重...")
    print("-" * 80)
    
    deduplicator = Deduplicator()
    unique_papers, duplicate_papers = deduplicator.deduplicate_papers(papers_dict)
    
    print(f"✅ 去重完成: 新增{len(unique_papers)}, 重复{len(duplicate_papers)}\n")
    
    # ===== 第3步：筛选和分类 =====
    print("🏷️  第3步：论文筛选与分类...")
    print("-" * 80)
    
    filter_obj = PaperFilter(min_relevance_score=0.0)
    filtered_papers, rejected = filter_obj.filter_and_rank(unique_papers, sort_by='relevance_score')
    
    print(f"✅ 筛选完成: 通过{len(filtered_papers)}, 被过滤{len(rejected)}\n")
    
    # 将AI总结数量从5篇改为10篇
    test_papers = [p.to_dict() for p in filtered_papers[:10]]
    
    # ===== 第4步：AI总结提取 =====
    print("🤖 第4步：AI核心思想提取...")
    print("-" * 80)
    
    deepseek_config = config_manager.get_deepseek_config()
    
    if not deepseek_config.get('api_key'):
        print("❌ DeepSeek API密钥未配置！")
        print("   请在 .env 文件中设置 DEEPSEEK_API_KEY")
        return
    
    print(f"📋 准备提取 {len(test_papers)} 篇论文的核心思想...\n")
    
    extractor = IdeaExtractor(deepseek_config)
    extracted_ideas, stats = await extractor.extract_batch_papers(test_papers, batch_size=2)
    
    # ===== 结果展示 =====
    print("\n" + "="*80)
    print("📊 AI总结提取结果")
    print("="*80)
    print(f"总数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"备选: {stats['fallback']}")
    print(f"失败: {stats['error']}")
    print(f"耗时: {stats['processing_time']:.2f}秒")
    print("="*80 + "\n")
    
    # 详细显示提取结果
    for i, idea in enumerate(extracted_ideas, 1):
        print(f"【论文 {i}】")
        print(f"论文ID: {idea.paper_id}")
        print(f"标题: {idea.title}")
        print(f"作者: {', '.join(idea.authors[:3])}...")
        print(f"发布: {idea.published[:10]}")
        print(f"状态: {idea.extraction_status}")
        
        if idea.extraction_error:
            print(f"错误: {idea.extraction_error}")
        
        print(f"\n📝 原始摘要 (前200字):")
        print(f"{idea.summary[:200]}...\n")
        
        print(f"🤖 AI生成总结:")
        print(f"{idea.ai_summary}\n")
        
        print(f"🔗 链接: {idea.arxiv_url}\n")
        print("-" * 80 + "\n")
    
    print("✅ 测试完成！\n")


if __name__ == '__main__':
    asyncio.run(main())
