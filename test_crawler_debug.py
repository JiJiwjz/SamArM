#!/usr/bin/env python3
"""
爬虫调试脚本 - 诊断arxiv查询问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arxiv
from src.config import ConfigManager

def test_arxiv_connection():
    """测试arxiv连接"""
    print("=" * 60)
    print("1️⃣  测试arxiv连接...")
    print("=" * 60)
    
    try:
        client = arxiv.Client()
        # 尝试一个简单的查询
        search = arxiv.Search(query="cat:cs.CV", max_results=5)
        results = list(client.results(search))
        print(f"✅ arxiv连接正常，获取到 {len(results)} 篇论文")
        return True
    except Exception as e:
        print(f"❌ arxiv连接失败: {e}")
        return False


def test_keyword_search():
    """测试关键词搜索"""
    print("\n" + "=" * 60)
    print("2️⃣  测试关键词搜索...")
    print("=" * 60)
    
    client = arxiv.Client(page_size=10, delay_seconds=3, num_retries=3)
    
    keywords = [
        "image denoising",
        "image deraining",
        "reinforcement learning",
        "embodied AI"
    ]
    
    for keyword in keywords:
        print(f"\n🔍 搜索关键词: '{keyword}'")
        try:
            search = arxiv.Search(
                query=f"all:{keyword}",
                max_results=10,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            results = list(client.results(search))
            print(f"   ✅ 获取到 {len(results)} 篇论文")
            if results:
                print(f"   最新论文: {results[0].title[:60]}...")
        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")


def test_category_search():
    """测试分类搜索"""
    print("\n" + "=" * 60)
    print("3️⃣  测试分类搜索...")
    print("=" * 60)
    
    client = arxiv.Client(page_size=10, delay_seconds=3, num_retries=3)
    
    categories = ["cs.CV", "cs.AI", "cs.LG"]
    
    for category in categories:
        print(f"\n📁 搜索分类: '{category}'")
        try:
            search = arxiv.Search(
                query=f"cat:{category}",
                max_results=10,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            results = list(client.results(search))
            print(f"   ✅ 获取到 {len(results)} 篇论文")
            if results:
                print(f"   最新论文: {results[0].title[:60]}...")
        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")


def test_combined_search():
    """测试组合搜索（关键词 OR 关键词）"""
    print("\n" + "=" * 60)
    print("4️⃣  测试组合搜索（关键词OR）...")
    print("=" * 60)
    
    client = arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)
    
    # 使用 OR 逻辑代替 AND
    query = "(all:image denoising) OR (all:image deraining) OR (all:reinforcement learning) OR (all:embodied AI)"
    
    print(f"查询语句: {query}\n")
    
    try:
        search = arxiv.Search(
            query=query,
            max_results=50,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending
        )
        results = list(client.results(search))
        print(f"✅ 获取到 {len(results)} 篇论文")
        
        # 显示前5篇
        print("\n📚 前5篇论文:")
        for i, paper in enumerate(results[:5], 1):
            print(f"\n  {i}. {paper.title[:70]}")
            print(f"     作者: {', '.join([a.name for a in paper.authors[:2]])}...")
            print(f"     发布: {paper.published.date()}")
            print(f"     链接: {paper.entry_id}")
    except Exception as e:
        print(f"❌ 搜索失败: {e}")


def test_config_manager():
    """测试配置管理器"""
    print("\n" + "=" * 60)
    print("5️⃣  测试配置管理器...")
    print("=" * 60)
    
    config = ConfigManager()
    arxiv_config = config.get_arxiv_config()
    
    print(f"\n📋 当前arxiv配置:")
    print(f"  关键词: {arxiv_config.get('keywords')}")
    print(f"  分类: {arxiv_config.get('categories')}")
    print(f"  最大结果: {arxiv_config.get('max_results')}")
    print(f"  排序方式: {arxiv_config.get('sort_by')}")


def main():
    """运行所有诊断"""
    print("\n" + "🔧" * 30)
    print("   arxiv爬虫诊断工具")
    print("🔧" * 30 + "\n")
    
    # 测试配置
    test_config_manager()
    
    # 测试连接
    if not test_arxiv_connection():
        print("\n❌ 无法连接到arxiv，请检查网络连接")
        return
    
    # 测试关键词搜索
    test_keyword_search()
    
    # 测试分类搜索
    test_category_search()
    
    # 测试组合搜索
    test_combined_search()
    
    print("\n" + "✅" * 30)
    print("   诊断完成！")
    print("✅" * 30 + "\n")


if __name__ == '__main__':
    main()
