"""
DailyJob - 论文日报编排任务
串联：爬取 -> 去重 -> 筛选 -> AI总结 -> 质量评估 -> 邮件格式化 -> 邮件发送 -> 落盘
"""

import os
import asyncio
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from src.config import ConfigManager
from src.crawler import ArxivCrawler
from src.filter import PaperFilter, Deduplicator
from src.extractor import IdeaExtractor, ExtractedIdea
from src.evaluator import PaperEvaluator  # 🆕 导入质量评估器
from src.sender import EmailFormatter, EmailSender
from .delivery_state import DeliveryState

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
            quality_data = quality_map.get(pid) or PaperEvaluator._create_fallback_quality(paper).to_dict()
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
                'weaknesses': quality_data.get('weaknesses', []),
                'evaluation_status': quality_data.get('evaluation_status', 'fallback')
            }
            merged.append(paper_with_quality)
        return merged

    async def _extract_async(self, filtered_dict: List[Dict[str, Any]], batch_size: int) -> List[Dict[str, Any]]:
        """内部异步AI总结流程"""
        deepseek_config = self.cm.get_deepseek_config()
        ideas: List[ExtractedIdea] = []
        try:
            extractor = IdeaExtractor(deepseek_config, evaluate_quality=False)
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
            return [PaperEvaluator._create_fallback_quality(p).to_dict() for p in papers]

    @staticmethod
    def _wait_until(send_at):
        if not send_at:
            return
        hh, mm = map(int, send_at.split(':'))
        now = datetime.now(timezone(timedelta(hours=8)))
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        while now < target:
            seconds = (target - now).total_seconds()
            logger.info('日报已准备好，等待北京时间 %s 投递（剩余 %.0f 秒）', send_at, seconds)
            time.sleep(min(30, seconds))
            now = datetime.now(timezone(timedelta(hours=8)))

    def _write_outputs(self, html, stats, html_out=None):
        date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d')
        html_path = html_out or os.path.join(self.output_dir, f'daily_{date}.html')
        os.makedirs(os.path.dirname(os.path.abspath(html_path)), exist_ok=True)
        with open(html_path, 'w', encoding='utf-8') as stream:
            stream.write(html)
        report_path = os.path.join(self.output_dir, f'report_{date}.json')
        stats.update(html_out=html_path, report_out=report_path,
                     end_at=datetime.now(timezone.utc).isoformat())
        with open(report_path, 'w', encoding='utf-8') as stream:
            json.dump(stats, stream, ensure_ascii=False, indent=2)

    def _deliver(self, state, recipients, config, dedup, state_store, persist, send_at):
        self._wait_until(send_at)
        sender = EmailSender(config)
        sent = set(state.get('sent', []))
        result = {'total': len(recipients), 'success': 0, 'failed': 0,
                  'already_sent': 0, 'failed_recipients': [], 'failed_reasons': {}}
        for recipient in recipients:
            key = DeliveryState.recipient_key(recipient)
            if key in sent:
                result['already_sent'] += 1
                continue
            ok, message = sender.send_email(recipient, state['subject'], state['html'], state['plain'])
            if ok:
                result['success'] += 1
                sent.add(key)
                state['sent'] = sorted(sent)
                if persist:
                    state_store.save(state)
            else:
                result['failed'] += 1
                result['failed_recipients'].append(recipient)
                result['failed_reasons'][recipient] = message
        if result['failed'] == 0:
            for paper in state['papers']:
                dedup.mark_as_processed(paper)
        return result

    def run(self, days_back=3, top_n=10, summary_batch_size=3, only_new=True,
            send_email=True, html_out=None, once_per_day=False, send_at=None):
        if min(days_back, top_n, summary_batch_size) < 1:
            raise ValueError('days_back、top_n、batch_size 必须为正整数')
        start = datetime.now(timezone.utc)
        date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
        email_config = self.cm.get_email_config()
        raw_recipients = email_config.get('recipients', [])
        if isinstance(raw_recipients, str):
            raw_recipients = raw_recipients.split('|')
        recipients = list(dict.fromkeys(r.strip() for r in raw_recipients if r.strip()))
        if send_email:
            if not recipients or not all(email_config.get(k) for k in
                                         ['sender_email', 'sender_password', 'smtp_server']):
                raise ValueError('邮件配置不完整，不能跳过发送后报告成功')
        dedup = Deduplicator()
        state_store = DeliveryState()
        state = state_store.load(date) if send_email and once_per_day else None
        if state and all(DeliveryState.recipient_key(r) in state.get('sent', []) for r in recipients):
            # Repair paper cache if a previous process exited after SMTP but before marking.
            for paper in state['papers']:
                dedup.mark_as_processed(paper)
            stats = {**state['stats'], 'skipped': 'already delivered today'}
            self._write_outputs(state['html'], stats, html_out)
            return stats
        if state:
            logger.info('恢复当天未完成投递，复用同一份日报')
            stats = dict(state['stats'])
            html = state['html']
        else:
            stats = {'start_at': start.isoformat(), 'days_back': days_back,
                     'top_n': top_n, 'only_new': only_new, 'send_email': send_email}
            config = self.cm.get_arxiv_config()
            crawler = ArxivCrawler(config)
            crawler.set_search_mode(config.get('search_mode', 'keyword_only'))
            filter_obj = PaperFilter(min_relevance_score=self.cm.get('filter.min_relevance_score', 0.01),
                                     robotics_only=self.cm.get('filter.robotics_only', True))
            # Fetch once; widen the local window without repeating arXiv requests.
            max_window = max(days_back, 7)
            papers = [p.to_dict() for p in crawler.fetch_papers(days_back=max_window)]
            if crawler.last_error:
                raise RuntimeError('arXiv 检索失败：' + crawler.last_error)
            stats['fetched'] = len(papers)
            unique, duplicates = dedup.deduplicate_papers(papers, mark_processed=False)
            candidates = unique if only_new else papers
            stats.update(unique=len(unique), duplicates=len(duplicates), candidates=len(candidates))
            filtered = []
            for window in sorted({days_back, 2, 3, 5, max_window}):
                if window < days_back:
                    continue
                cutoff = start - timedelta(days=window)
                recent = [p for p in candidates if
                          datetime.fromisoformat(p['published'].replace('Z', '+00:00')).astimezone(
                              timezone.utc) >= cutoff]
                filtered_papers, rejected = filter_obj.filter_and_rank(recent)
                stats['rejected'] = len(rejected)
                filtered = [p.to_dict() for p in filtered_papers[:top_n]]
                stats['used_days_back'] = window
                if filtered:
                    break
            stats['filtered'] = len(filtered)
            for paper in filtered:
                image = crawler.fetch_overview_image(paper.get('paper_id', ''))
                if image:
                    paper['overview_image'] = image
            ideas = asyncio.run(self._extract_async(filtered, summary_batch_size)) if filtered else []
            stats['summarized'] = len(ideas)
            stats['summary_fallback'] = sum(p.get('extraction_status') != 'success' for p in ideas)
            merged = self._merge_meta(filtered, ideas)
            qualities = asyncio.run(self._evaluate_async(merged, summary_batch_size)) if merged else []
            stats['evaluated'] = sum(q.get('evaluation_status') == 'success' for q in qualities)
            stats['evaluation_pending'] = len(merged) - stats['evaluated']
            final_papers = self._merge_quality(merged, qualities)
            final_papers.sort(key=lambda p: (p.get('quality_score') or 0) * 0.7 +
                              (p.get('relevance_score') or 0) * 3, reverse=True)
            formatter = EmailFormatter()
            html, stats['email_stats'] = formatter.format_papers_to_html(final_papers)
            plain = formatter.generate_plain_text_email(final_papers)
            prefix = email_config.get('subject_prefix', '【机器人学习日报】')
            subject = f'{prefix}{date}' + ('（暂无新论文）' if not final_papers else '')
            state = {'date': date, 'sent': [], 'papers': final_papers,
                     'html': html, 'plain': plain, 'subject': subject, 'stats': stats}
            if send_email and once_per_day:
                state_store.save(state)
        self._write_outputs(html, stats, html_out)
        if send_email:
            try:
                result = self._deliver(state, recipients, email_config, dedup, state_store,
                                       once_per_day, send_at)
            except Exception as error:
                stats['delivery_error'] = str(error)
                self._write_outputs(html, stats, html_out)
                raise
            stats['send_result'] = result
            self._write_outputs(html, stats, html_out)
            if once_per_day:
                state['stats'] = stats
                state_store.save(state)
            if result['failed']:
                raise RuntimeError(f"邮件投递失败 {result['failed']} 封；日报已保存，可补跑未成功的收件人")
        return stats
