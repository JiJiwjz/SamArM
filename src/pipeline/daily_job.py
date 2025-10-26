"""
DailyJob - 论文日报编排任务
串联：爬取 -> 去重 -> 筛选 -> AI总结 -> 质量评估 -> 邮件格式化 -> 邮件发送 -> 落盘
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.config import ConfigManager
from src.crawler import ArxivCrawler
from src.filter import PaperFilter, Deduplicator
from src.extractor import IdeaExtractor, ExtractedIdea
from src.evaluator import PaperEvaluator  # 🆕 导入质量评估器
from src.sender import EmailFormatter, EmailSender

logger = logging.getLogger(__name__)


class DailyJob:
    """论文日报编排任务"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.cm = config_manager or ConfigManager()
        self.output_dir = os.path.join(os.getcwd(), "out")
        os.makedirs(self.output_dir, exist_ok=True)

    def _merge_meta(self, metas: List[Dict[str, Any]], ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将筛选阶段元数据合并进AI总结结果，保留 topic_category / relevance_score / matched_keywords 等"""
        meta_map = {m.get("paper_id"): m for m in metas}
        merged = []
        for idea in ideas:
            pid = idea.get("paper_id")
            base = meta_map.get(pid, {})
            merged.append({**base, **idea})
        return merged
    
    def _merge_quality(self, papers: List[Dict[str, Any]], qualities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """🆕 将质量评估结果合并到论文数据中"""
        quality_map = {q.get("paper_id"): q for q in qualities}
        merged = []
        for paper in papers:
            pid = paper.get("paper_id")
            quality_data = quality_map.get(pid, {})
            # 提取关键评估字段
            paper_with_quality = {
                **paper,
                'quality_score': quality_data.get('overall_score'),
                'quality_level': quality_data.get('quality_level'),
                'quality_reasoning': quality_data.get('reasoning'),
                'innovation_score': quality_data.get('innovation_score'),
                'practicality_score': quality_data.get('practicality_score'),
                'technical_depth_score': quality_data.get('technical_depth_score'),
                'experimental_rigor_score': quality_data.get('experimental_rigor_score'),
                'impact_potential_score': quality_data.get('impact_potential_score'),
                'strengths': quality_data.get('strengths', []),
                'weaknesses': quality_data.get('weaknesses', [])
            }
            merged.append(paper_with_quality)
        return merged

    async def _extract_async(self, filtered_dict: List[Dict[str, Any]], batch_size: int) -> List[Dict[str, Any]]:
        """内部异步AI总结流程"""
        deepseek_config = self.cm.get_deepseek_config()
        ideas: List[ExtractedIdea] = []
        try:
            extractor = IdeaExtractor(deepseek_config)
            extracted_ideas, stats = await extractor.extract_batch_papers(filtered_dict, batch_size=batch_size)
            logger.info(f"AI总结完成: 成功{stats['success']} 备选{stats['fallback']} 失败{stats['error']} 耗时{stats['processing_time']:.2f}s")
            ideas = extracted_ideas
        except Exception as e:
            logger.warning(f"AI总结不可用，使用摘要备选方案。原因: {e}")
            # 退化为直接把摘要作为 ai_summary
            for p in filtered_dict:
                ideas.append(ExtractedIdea(
                    paper_id=p.get('paper_id', ''),
                    title=p.get('title', ''),
                    authors=p.get('authors', []),
                    summary=p.get('summary', ''),
                    ai_summary=(p.get('summary') or '')[:300] + ('...' if len(p.get('summary','')) > 300 else ''),
                    key_points=None,
                    extraction_status='fallback',
                    extraction_error='DeepSeek unavailable',
                    extraction_time=datetime.utcnow().isoformat(),
                    published=p.get('published', ''),
                    arxiv_url=p.get('arxiv_url', '')
                ))
        return [i.to_dict() for i in ideas]
    
    async def _evaluate_async(self, papers: List[Dict[str, Any]], batch_size: int) -> List[Dict[str, Any]]:
        """🆕 内部异步质量评估流程"""
        deepseek_config = self.cm.get_deepseek_config()
        try:
            evaluator = PaperEvaluator(deepseek_config)
            qualities, stats = await evaluator.evaluate_batch_papers(papers, batch_size=batch_size)
            logger.info(f"质量评估完成: 成功{stats['success']} 备选{stats['fallback']} 失败{stats['error']} 耗时{stats['processing_time']:.2f}s")
            return [q.to_dict() for q in qualities]
        except Exception as e:
            logger.warning(f"质量评估不可用: {e}")
            return []

    def run(self,
            days_back: int = 3,
            top_n: int = 10,
            summary_batch_size: int = 3,
            only_new: bool = True,
            send_email: bool = True,
            html_out: Optional[str] = None) -> Dict[str, Any]:
        """
        执行一次日报任务

        Args:
            days_back: 回溯天数
            top_n: 发送前取TopN篇
            summary_batch_size: AI并发批大小
            only_new: True仅推送新论文（已处理过的不再推送）
            send_email: 是否发送邮件
            html_out: 指定HTML输出路径，默认写入 out/daily_YYYYMMDD.html

        Returns:
            统计信息字典
        """
        start = datetime.utcnow()
        stats: Dict[str, Any] = {
            "start_at": start.isoformat(),
            "days_back": days_back,
            "top_n": top_n,
            "only_new": only_new,
            "send_email": send_email
        }

        # 1) 爬取
        arxiv_config = self.cm.get_arxiv_config()
        crawler = ArxivCrawler(arxiv_config)
        papers = crawler.fetch_papers(days_back=days_back)
        papers_dict = [p.to_dict() for p in papers]
        stats["fetched"] = len(papers_dict)
        logger.info(f"爬取完成: {len(papers_dict)} 篇")

        # 2) 去重（持久缓存）
        dedup = Deduplicator()
        unique_papers, duplicate_papers = dedup.deduplicate_papers(papers_dict)
        if only_new:
            candidate = unique_papers
        else:
            candidate = papers_dict
        stats["unique"] = len(unique_papers)
        stats["duplicates"] = len(duplicate_papers)
        stats["candidates"] = len(candidate)
        logger.info(f"去重完成: 新增{len(unique_papers)} 重复{len(duplicate_papers)} 用于筛选{len(candidate)}")

        # 3) 筛选与排序（按相关性）
        filter_obj = PaperFilter(min_relevance_score=0.0)
        filtered_papers, _ = filter_obj.filter_and_rank(candidate, sort_by='relevance_score')
        filtered_dict = [p.to_dict() for p in filtered_papers]
        if top_n and len(filtered_dict) > top_n:
            filtered_dict = filtered_dict[:top_n]
        stats["filtered"] = len(filtered_dict)
        logger.info(f"筛选完成: 选取{len(filtered_dict)} 篇用于AI总结")

        # 4) AI 总结（异步）
        ideas_dict: List[Dict[str, Any]] = asyncio.run(self._extract_async(filtered_dict, batch_size=summary_batch_size))
        stats["summarized"] = len(ideas_dict)

        # 5) 合并元数据，确保主题/相关性在邮件中显示
        merged_papers = self._merge_meta(filtered_dict, ideas_dict)
        
        # 🆕 6) 质量评估（异步，使用相同的batch_size）
        quality_dict: List[Dict[str, Any]] = asyncio.run(self._evaluate_async(merged_papers, batch_size=summary_batch_size))
        stats["evaluated"] = len(quality_dict)
        
        # 🆕 7) 合并质量评估结果
        final_papers = self._merge_quality(merged_papers, quality_dict)
        
        # 🆕 8) 按质量评分重新排序（质量评分优先，相关性次之）
        final_papers = sorted(
            final_papers,
            key=lambda p: (
                p.get('quality_score', 0) * 0.7 +  # 质量评分权重70%
                p.get('relevance_score', 0) * 10 * 0.3  # 相关性权重30%
            ),
            reverse=True
        )

        # 9) 格式化邮件
        formatter = EmailFormatter()
        html, email_stats = formatter.format_papers_to_html(final_papers)
        plain = formatter.generate_plain_text_email(final_papers)
        stats["email_stats"] = email_stats

        # 10) 发送邮件（可选）
        sent_stats = None
        if send_email:
            email_config = self.cm.get_email_config()
            recipients = email_config.get('recipients', [])
            if recipients and email_config.get('sender_email'):
                sender = EmailSender(email_config)
                subject = f"【Arxiv论文日报】{datetime.utcnow().strftime('%Y-%m-%d')}"
                # 🔧 修正：使用正确的方法名 send_batch_emails
                sent_stats = sender.send_batch_emails(recipients, subject, html, plain)
                stats["send_result"] = sent_stats
                logger.info(f"邮件发送完成: {sent_stats}")
            else:
                logger.warning("邮件配置不完整，跳过发送")

        # 11) 落盘
        if not html_out:
            html_out = os.path.join(self.output_dir, f"daily_{datetime.utcnow().strftime('%Y%m%d')}.html")
        with open(html_out, 'w', encoding='utf-8') as f:
            f.write(html)
        logger.info(f"HTML已保存: {html_out}")

        report_path = os.path.join(self.output_dir, f"report_{datetime.utcnow().strftime('%Y%m%d')}.json")
        import json
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        logger.info(f"报告已保存: {report_path}")

        stats["html_out"] = html_out
        stats["report_out"] = report_path
        stats["end_at"] = datetime.utcnow().isoformat()
        
        return stats
