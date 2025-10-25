#!/usr/bin/env python3
"""
测试邮件发送模块
完整流程：爬取 -> 去重 -> 筛选 -> AI总结 -> 格式化邮件 -> 发送
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
from src.sender import EmailFormatter, EmailSender


async def main():
    """完整测试流程"""
    
    print("\n" + "="*80)
    print("🚀 完整流程测试：爬取 -> 去重 -> 筛选 -> AI总结 -> 邮件格式化")
    print("="*80 + "\n")
    
    config_manager = ConfigManager()
    
    # ===== 第1步：爬取论文 =====
    print("📥 第1步：从arxiv爬取论文...")
    arxiv_config = config_manager.get_arxiv_config()
    crawler = ArxivCrawler(arxiv_config)
    papers = crawler.fetch_papers(days_back=3)
    papers_dict = [p.to_dict() for p in papers]
    print(f"✅ 成功爬取 {len(papers_dict)} 篇论文\n")
    
    # ===== 第2步：去重 =====
    print("🔄 第2步：论文去重...")
    deduplicator = Deduplicator()
    unique_papers, _ = deduplicator.deduplicate_papers(papers_dict)
    print(f"✅ 去重完成: {len(unique_papers)} 篇新论文\n")
    
    # ===== 第3步：筛选 =====
    print("🏷️  第3步：论文筛选与分类...")
    filter_obj = PaperFilter()
    filtered_papers, _ = filter_obj.filter_papers(unique_papers)
    # 将AI总结篇数从5改为10
    filtered_dict = [p.to_dict() for p in filtered_papers[:10]]
    print(f"✅ 筛选完成: {len(filtered_dict)} 篇论文用于AI总结\n")
    
    # ===== 第4步：AI总结 =====
    print("🤖 第4步：AI核心思想提取...")
    deepseek_config = config_manager.get_deepseek_config()
    extractor = IdeaExtractor(deepseek_config)
    extracted_ideas, stats = await extractor.extract_batch_papers(filtered_dict, batch_size=2)
    
    # 转换为字典
    ideas_dict = [idea.to_dict() for idea in extracted_ideas]
    print(f"✅ AI总结完成: {stats['success']} 成功, {stats['fallback']} 备选\n")
    print(f"AI总结条目数: {len(ideas_dict)}")
    
    # ===== 合并分类与相关性字段，确保邮件展示主题/分数 =====
    meta_map = {p['paper_id']: p for p in filtered_dict}
    merged_papers = []
    for idea in ideas_dict:
        pid = idea.get('paper_id')
        meta = meta_map.get(pid, {})
        merged = {**meta, **idea}  # meta在前，保留topic_category/relevance_score等
        merged_papers.append(merged)
    
    non_unknown = sum(1 for p in merged_papers if p.get('topic_category') not in (None, 'unknown'))
    non_zero_rel = sum(1 for p in merged_papers if p.get('relevance_score', 0) > 0)
    print(f"🔎 合并后：有主题的论文数={non_unknown}，相关性>0的论文数={non_zero_rel}\n")
    
    # ===== 第5步：邮件格式化 =====
    print("📧 第5步：邮件格式化...")
    formatter = EmailFormatter()
    html_content, email_stats = formatter.format_papers_to_html(merged_papers)
    plain_content = formatter.generate_plain_text_email(merged_papers)
    
    print(f"✅ 邮件格式化完成")
    print(f"   HTML长度: {len(html_content)} 字节")
    print(f"   纯文本长度: {len(plain_content)} 字节\n")
    
    # ===== 第6步：预览（纯文本） =====
    print("="*80)
    print("📧 邮件内容预览（纯文本版本）")
    print("="*80 + "\n")
    print(plain_content[:1500])
    print("\n... (内容过长，已省略) ...\n")
    
    # ===== 第7步：邮件发送 =====
    print("="*80)
    print("📬 邮件发送测试")
    print("="*80 + "\n")
    
    email_config = config_manager.get_email_config()
    recipients = email_config.get('recipients', [])
    
    if not recipients or not email_config.get('sender_email'):
        print("⚠️  邮件配置不完整，跳过实际发送")
        print(f"   配置的收件人: {recipients}")
        print(f"   配置的发送者: {email_config.get('sender_email')}")
        print("\n💡 要启用邮件发送，请在 .env 文件中配置：")
        print("   - SENDER_EMAIL: 你的邮箱")
        print("   - SENDER_PASSWORD: 邮箱授权码")
        print("   - RECIPIENT_EMAILS: 收件人邮箱（用|分隔）")
        return
    
    try:
        sender = EmailSender(email_config)
        print("✅ 邮件发送器初始化成功\n")
        
        print("📋 发送配置:")
        print(f"  发送者: {email_config.get('sender_email')}")
        print(f"  收件人: {recipients}")
        print(f"  主题: 【Arxiv论文日报】{datetime.utcnow().strftime('%Y-%m-%d')}")
        print(f"  方式: HTML + 纯文本")
        
        confirm = input("\n是否确认发送？(yes/no): ").strip().lower()
        
        if confirm == 'yes':
            subject = f"【Arxiv论文日报】{datetime.utcnow().strftime('%Y-%m-%d')}"
            # 关键变更：将批量发送的重试次数设置为1
            stats = sender.send_batch_emails(
                recipients, subject, html_content, plain_content, max_retries=1
            )
            
            print(f"\n📊 发送统计:")
            print(f"  总数: {stats['total']}")
            print(f"  成功: {stats['success']}")
            print(f"  失败: {stats['failed']}")
            
            if stats['failed_recipients']:
                print(f"\n  失败的收件人:")
                for recipient, reason in stats['failed_reasons'].items():
                    print(f"    - {recipient}: {reason}")
        else:
            print("❌ 已取消发送")
    
    except Exception as e:
        print(f"❌ 邮件发送器初始化失败: {e}")
        print("\n💡 请检查 .env 文件中的邮件配置")


if __name__ == '__main__':
    asyncio.run(main())
