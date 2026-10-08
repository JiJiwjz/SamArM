"""Offline regression tests: no real API calls or emails."""
import asyncio
import json
import os
import tempfile
import unittest
import smtplib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from src.filter import PaperFilter, Deduplicator
from src.evaluator.paper_evaluator import PaperEvaluator
from src.extractor.api_request import request_completion
from src.extractor.deepseek_client import DeepSeekBatchProcessor
from src.pipeline.daily_job import DailyJob
from src.sender import EmailFormatter
from src.sender.email_sender import EmailSender
from src.crawler.arxiv_crawler import TimeoutAdapter, ArxivCrawler


def paper(pid='one', title='In-context learning for robotic manipulation', summary='A robot arm grasps objects.'):
    return {'paper_id': pid, 'title': title, 'summary': summary, 'authors': ['Test'],
            'published': datetime.now(timezone.utc).isoformat(), 'arxiv_url': 'https://arxiv.org/abs/test'}


class ScopeTests(unittest.TestCase):
    def test_robot_topics_and_exclusions(self):
        candidates = [
            paper('arm'),
            paper('hand', 'Reinforcement learning for dexterous hands'),
            paper('vla', 'Vision language action models', 'A robot learns manipulation.'),
            paper('il', 'Imitation learning from demonstrations', 'A robot arm learns a policy.'),
            paper('general', 'In-context learning in language models', 'Language-only benchmarks.'),
            paper('humanoid', 'Humanoid robot reinforcement learning', 'Dexterous manipulation.'),
            paper('navigation', 'Reinforcement learning for robot navigation', 'Mobile navigation.'),
            paper('image', 'Image restoration', 'Image denoising.'),
        ]
        selected, rejected = PaperFilter(robotics_only=True).filter_papers(candidates)
        self.assertEqual({p.paper_id for p in selected}, {'arm', 'hand', 'vla', 'il'})
        self.assertEqual(len(rejected), 4)

    def test_short_acronym_does_not_match_substring(self):
        selected, _ = PaperFilter(robotics_only=True).filter_papers(
            [paper(title='VLA for robots', summary='Robot policies.'),
             paper('other', 'VLAD descriptors for robots', 'Visual descriptors.')])
        self.assertEqual([p.paper_id for p in selected], ['one'])

    def test_empty_report_is_explicit(self):
        html, _ = EmailFormatter().format_papers_to_html([])
        self.assertIn('暂无符合范围的新论文', html)
        self.assertIn('机器人学习', html)
        self.assertNotIn('Image Restoration', html)


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.result = {field: 7 for field in ['innovation_score', 'practicality_score',
                      'technical_depth_score', 'experimental_rigor_score', 'impact_potential_score']}
        self.result.update(reasoning='Based on the abstract only.', strengths=['Method'], weaknesses=['Needs full text'])

    def test_valid_fenced_json_and_computed_score(self):
        result = PaperEvaluator._validate_result('```json\n' + json.dumps(self.result) + '\n```')
        self.assertEqual(result['overall_score'], 7)
        self.assertEqual(result['quality_level'], '优秀')

    def test_missing_out_of_range_and_nonfinite_scores_are_rejected(self):
        for value in [None, 0, 11, '7', True, float('nan'), float('inf')]:
            with self.subTest(value=value):
                self.result['innovation_score'] = value
                with self.assertRaises(ValueError):
                    PaperEvaluator._validate_result(json.dumps(self.result))

    def test_fallback_never_invents_a_quality_score(self):
        quality = PaperEvaluator._create_fallback_quality({'relevance_score': 1})
        self.assertIsNone(quality.overall_score)
        self.assertIsNone(quality.innovation_score)


class SmtpTests(unittest.TestCase):
    def test_quit_failure_after_data_acceptance_is_success(self):
        sender = EmailSender({'sender_email': 'a@example.invalid', 'sender_password': 'fake',
                              'smtp_server': 'smtp.example.invalid', 'smtp_port': 465})
        with patch('src.sender.email_sender.smtplib.SMTP_SSL') as server:
            server.return_value.__exit__.side_effect = smtplib.SMTPServerDisconnected('QUIT failed')
            ok, _ = sender.send_email('b@example.invalid', 'test', '<p>test</p>')
        self.assertTrue(ok)

    def test_disconnect_during_data_is_not_claimed_successful(self):
        sender = EmailSender({'sender_email': 'a@example.invalid', 'sender_password': 'fake',
                              'smtp_server': 'smtp.example.invalid', 'smtp_port': 465})
        with patch('src.sender.email_sender.smtplib.SMTP_SSL') as server:
            server.return_value.__enter__.return_value.send_message.side_effect = smtplib.SMTPServerDisconnected('DATA failed')
            ok, _ = sender.send_email('b@example.invalid', 'test', '<p>test</p>')
        self.assertFalse(ok)

    def test_arxiv_request_timeout_is_bounded(self):
        with patch('requests.adapters.HTTPAdapter.send') as parent:
            TimeoutAdapter(timeout=30).send(MagicMock(), timeout=None)
        self.assertEqual(parent.call_args.kwargs['timeout'], (10, 30))

    def test_relevance_sort_does_not_stop_at_first_old_entry(self):
        with patch('src.crawler.arxiv_crawler.arxiv.Client') as client:
            old = MagicMock(published=datetime.now(timezone.utc) - timedelta(days=10))
            recent = MagicMock(published=datetime.now(timezone.utc))
            client.return_value.results.return_value = [old, recent]
            crawler = ArxivCrawler({'keywords': ['imitation learning'], 'sort_by': 'relevance',
                                    'robotics_only': True})
            crawler.set_search_mode('keyword_only')
            crawler._parse_paper = MagicMock(return_value=MagicMock(title='Robot imitation learning'))
            result = crawler.fetch_papers(days_back=1)
            search = client.return_value.results.call_args.args[0]
        self.assertEqual(len(result), 1)
        self.assertIn('submittedDate:[', search.query)
        self.assertIn('cat:cs.RO', search.query)


class Response:
    def __init__(self, status=200, content='ok', finish_reason='stop'):
        self.status = status
        self.content = content
        self.finish_reason = finish_reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def json(self):
        return {'choices': [{'message': {'content': self.content}, 'finish_reason': self.finish_reason}]}


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_truncated_rate_limited_responses_retry(self):
        for first in [Response(content=''), Response(content='{}', finish_reason='length'), Response(status=429)]:
            session = MagicMock()
            session.post.side_effect = [first, Response(content='complete')]
            with patch('src.extractor.api_request.asyncio.sleep', new_callable=AsyncMock):
                result = await request_completion(session, 'https://example.invalid', 'fake', {}, max_attempts=3)
            self.assertEqual(result, 'complete')
            self.assertEqual(session.post.call_count, 2)

    async def test_authentication_failure_does_not_retry(self):
        session = MagicMock()
        session.post.return_value = Response(status=401)
        result = await request_completion(session, 'https://example.invalid', 'fake', {})
        self.assertIsNone(result)
        self.assertEqual(session.post.call_count, 1)

    async def test_invalid_score_schema_retries_before_fallback(self):
        session = MagicMock()
        session.post.return_value = Response(content='{}')
        evaluator = PaperEvaluator({'api_key': 'fake'})
        with patch('src.extractor.api_request.asyncio.sleep', new_callable=AsyncMock):
            result = await evaluator._call_deepseek_api('Return JSON', session)
        self.assertIsNone(result)
        self.assertEqual(session.post.call_count, 3)
        payload = session.post.call_args.kwargs['json']
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['thinking'], {'type': 'disabled'})

    async def test_summary_only_avoids_duplicate_evaluation(self):
        client = MagicMock()
        client.summarize_paper = AsyncMock(return_value='Summary')
        client.evaluate_paper_quality = AsyncMock()
        summaries, evaluations = await DeepSeekBatchProcessor(client).process_papers_with_evaluation([paper()], evaluate=False)
        self.assertEqual(summaries[0][1], 'Summary')
        self.assertIsNone(evaluations[0][1])
        client.evaluate_paper_quality.assert_not_called()


class Config:
    def get_arxiv_config(self):
        return {'search_mode': 'keyword_only', 'robotics_only': True}

    def get_deepseek_config(self):
        return {}  # Exercises unavailable evaluator and summary fallback.

    def get_email_config(self):
        return {'recipients': ['a@example.invalid', 'b@example.invalid'],
                'sender_email': 'sender@example.invalid', 'sender_password': 'fake',
                'smtp_server': 'smtp.example.invalid', 'subject_prefix': '【机器人学习日报】'}

    def get(self, key, default=None):
        return default


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = os.getcwd()
        os.chdir(self.temp.name)
        self.crawler_patch = patch('src.pipeline.daily_job.ArxivCrawler')
        self.crawler = self.crawler_patch.start().return_value
        self.crawler.last_error = None
        item = MagicMock()
        item.to_dict.return_value = paper()
        self.crawler.fetch_papers.return_value = [item]
        self.crawler.fetch_overview_image.return_value = None
        self.sender_patch = patch('src.pipeline.daily_job.EmailSender')
        self.sender = self.sender_patch.start().return_value
        self.sender.send_email.return_value = (True, 'accepted')
        self.job = DailyJob(Config())

    def tearDown(self):
        self.sender_patch.stop()
        self.crawler_patch.stop()
        os.chdir(self.previous)
        self.temp.cleanup()

    def test_preview_does_not_consume_papers(self):
        stats = self.job.run(send_email=False)
        self.assertEqual(stats['filtered'], 1)
        self.assertEqual(stats['evaluation_pending'], 1)
        self.assertFalse(Path('data/processed_papers.json').exists())
        self.sender.send_email.assert_not_called()
        self.assertTrue(Path(stats['report_out']).exists())

    def test_early_preparation_waits_until_target_time(self):
        tz = timezone(timedelta(hours=8))
        with patch('src.pipeline.daily_job.datetime') as clock, patch('src.pipeline.daily_job.time.sleep') as sleep:
            clock.now.side_effect = [datetime(2026, 10, 8, 8, 59, 45, tzinfo=tz),
                                     datetime(2026, 10, 8, 9, 0, 1, tzinfo=tz)]
            self.job._wait_until('09:00')
        sleep.assert_called_once_with(15)

    def test_late_start_does_not_wait_until_tomorrow(self):
        with patch('src.pipeline.daily_job.datetime') as clock, patch('src.pipeline.daily_job.time.sleep') as sleep:
            clock.now.return_value = datetime(2026, 10, 8, 14, 0, tzinfo=timezone(timedelta(hours=8)))
            self.job._wait_until('09:00')
        sleep.assert_not_called()

    def test_once_per_day_preserves_delivery_and_skips_second_send(self):
        self.job.run(once_per_day=True)
        second = self.job.run(once_per_day=True)
        self.assertEqual(second['skipped'], 'already delivered today')
        self.assertEqual(self.sender.send_email.call_count, 2)
        self.assertEqual(self.crawler.fetch_papers.call_count, 1)
        self.assertTrue(Deduplicator().is_duplicate(paper())[0])

    def test_partial_failure_resumes_same_digest_only_for_failed_recipient(self):
        self.sender.send_email.side_effect = [(True, 'accepted'), (False, 'failed'), (True, 'accepted')]
        with self.assertRaises(RuntimeError):
            self.job.run(once_per_day=True)
        self.assertFalse(Deduplicator().is_duplicate(paper())[0])
        first_html = self.sender.send_email.call_args_list[0].args[2]
        result = self.job.run(once_per_day=True)
        self.assertEqual(result['send_result']['already_sent'], 1)
        self.assertEqual(self.sender.send_email.call_count, 3)
        self.assertEqual(self.sender.send_email.call_args.args[0], 'b@example.invalid')
        self.assertEqual(self.sender.send_email.call_args.args[2], first_html)
        self.assertEqual(self.crawler.fetch_papers.call_count, 1)
        self.assertTrue(Deduplicator().is_duplicate(paper())[0])

    def test_top_n_leaves_unselected_papers_available(self):
        other = MagicMock()
        other.to_dict.return_value = paper('two', 'Robot arm manipulation with demonstrations')
        self.crawler.fetch_papers.return_value.append(other)
        self.job.run(top_n=1, once_per_day=True)
        self.assertEqual(len(Deduplicator().paper_records), 1)

    def test_no_new_papers_send_honest_status_without_history(self):
        self.crawler.fetch_papers.return_value = []
        result = self.job.run(once_per_day=True)
        self.assertEqual(result['filtered'], 0)
        self.assertIn('暂无新论文', self.sender.send_email.call_args.args[1])
        self.assertIn('暂无符合范围的新论文', self.sender.send_email.call_args.args[2])

    def test_crawler_outage_fails_and_does_not_claim_empty_success(self):
        self.crawler.last_error = 'network outage'
        self.crawler.fetch_papers.return_value = []
        with self.assertRaisesRegex(RuntimeError, 'arXiv'):
            self.job.run(once_per_day=True)
        self.sender.send_email.assert_not_called()
        self.assertFalse(Path('data/daily_delivery.json').exists())

    def test_dedup_preview_removes_in_batch_duplicates_without_persisting(self):
        dedup = Deduplicator()
        unique, duplicates = dedup.deduplicate_papers([paper(), paper()], mark_processed=False)
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(duplicates), 1)
        self.assertFalse(Path('data/processed_papers.json').exists())


if __name__ == '__main__':
    unittest.main()
