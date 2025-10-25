#!/usr/bin/env python3
"""
详细诊断爬虫
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.crawler import ArxivCrawler
from src.config import ConfigManager
from datetime import datetime, timedelta

def main():
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    print("\n" + "="*60)
    print("详细爬虫诊断")
    print("="*60 + "\n")
    
    # 创建爬虫实例
    crawler = ArxivCrawler(arxiv_config)
    
    # 显示搜索查询
    query = crawler.build_search_query()
    print(f"📋 搜索查询语句:\n   {query}\n")
    
    # 手动执行搜索并显示详细信息
    import arxiv
    
    print("🔍 正在查询arxiv...\n")
    
    sort_criterion_map = {
        'submittedDate': arxiv.SortCriterion.SubmittedDate,
        'relevance': arxiv.SortCriterion.Relevance,
        'lastUpdatedDate': arxiv.SortCriterion.LastUpdatedDate,
    }
    sort_by = sort_criterion_map.get(crawler.sort_by, arxiv.SortCriterion.SubmittedDate)
    
    search = arxiv.Search(
        query=query,
        max_results=crawler.max_results,
        sort_by=sort_by,
        sort_order=arxiv.SortOrder.Descending
    )
    
    # 计算时间范围
    now = datetime.utcnow()
    cutoff_date = now - timedelta(days=1)
    
    print(f"⏰ 当前时间(UTC): {now}")
    print(f"⏰ 截止时间(UTC): {cutoff_date}\n")
    
    # 获取并显示所有结果
    count = 0
    passed_count = 0
    
    for i, entry in enumerate(crawler.client.results(search)):
        count += 1
        published_date = entry.published.replace(tzinfo=None)
        
        is_within_range = published_date >= cutoff_date
        status = "✅ PASS" if is_within_range else "❌ FILTERED"
        
        print(f"论文 #{count}: {status}")
        print(f"  标题: {entry.title[:60]}")
        print(f"  发布: {published_date}")
        print(f"  ID: {entry.entry_id}\n")
        
        if is_within_range:
            passed_count += 1
        else:
            print("  (发布时间早于截止时间，已被过滤)\n")
            # 停止显示更多已过滤的论文
            if passed_count == 0:
                break
        
        # 只显示前10个
        if count >= 10:
            break
    
    print(f"\n📊 结果统计:")
    print(f"  总查询数: {count}")
    print(f"  通过筛选: {passed_count}")
    print(f"  被过滤: {count - passed_count}")


if __name__ == '__main__':
    main()
