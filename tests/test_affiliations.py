import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from src.crawler.arxiv_crawler import ArxivCrawler
from src.extractor.affiliation_extractor import AffiliationExtractor
from src.sender import EmailFormatter


class HtmlAffiliationTests(unittest.TestCase):
    def test_structured_affiliations_deduplicate_and_remove_project_notes(self):
        soup = BeautifulSoup('''<div class="ltx_authors">
          <span class="ltx_role_affiliation">Affiliation: Example University</span>
          <span class="ltx_role_affiliation">Affiliation: Example University</span>
          <span class="ltx_role_affiliation">Affiliation: Second Institute
             <span>Project page <a href="https://example.invalid">website</a></span></span>
        </div>''', 'html.parser')
        names, _ = ArxivCrawler.parse_author_metadata(soup)
        self.assertEqual(names, ['Example University', 'Second Institute'])

    def test_numbered_affiliations_after_author_table(self):
        soup = BeautifulSoup('''<div class="ltx_authors"><span class="ltx_personname">
          <span>Test Author<sup>1</sup></span><br>
          <sup>1</sup> Nanjing University <sup>2</sup> Harbin Institute of Technology (Shenzhen)<br>
          <sup>3</sup> Australian National University <sup>4</sup> University of Technology Sydney
        </span></div>''', 'html.parser')
        names, _ = ArxivCrawler.parse_author_metadata(soup)
        self.assertEqual(names, ['Nanjing University', 'Harbin Institute of Technology (Shenzhen)',
                                 'Australian National University', 'University of Technology Sydney'])

    def test_metadata_affiliations_work_without_author_html(self):
        soup = BeautifulSoup('<meta name="citation_author_institution" content="Example University">', 'html.parser')
        names, _ = ArxivCrawler.parse_author_metadata(soup)
        self.assertEqual(names, ['Example University'])

    def test_metadata_and_overview_reuse_one_html_request(self):
        with patch('src.crawler.arxiv_crawler.requests.get') as get:
            get.return_value.status_code = 200
            get.return_value.text = '''<div class="ltx_authors"><span class="ltx_role_affiliation">Example University</span></div>
                                      <figure><img src="image.png"></figure>'''
            crawler = ArxivCrawler({})
            metadata = crawler.fetch_author_metadata('1234.56789v1')
            image = crawler.fetch_overview_image('1234.56789v1')
        self.assertEqual(get.call_count, 1)
        self.assertEqual(metadata['institutions'], ['Example University'])
        self.assertEqual(image, 'https://arxiv.org/html/image.png')

    def test_oversized_pdf_is_skipped_without_parsing(self):
        crawler = ArxivCrawler({})
        with (patch.object(crawler, '_get_html', return_value=(None, '')),
             patch('src.crawler.arxiv_crawler.requests.get') as get,
             patch.object(crawler, 'extract_pdf_author_text') as extract):
            get.return_value.__enter__.return_value.headers = {'Content-Length': str(20 * 1024 * 1024)}
            result = crawler.fetch_author_metadata('1234.56789', max_pdf_mb=1)
        self.assertEqual(result, {})
        extract.assert_not_called()

    def test_pdf_extraction_reads_first_page_only(self):
        with patch('pypdf.PdfReader') as reader:
            first, second = MagicMock(), MagicMock()
            first.extract_text.return_value = 'Test Author\nExample University\nAbstract'
            reader.return_value.pages = [first, second]
            text = ArxivCrawler.extract_pdf_author_text(b'%PDF-')
        self.assertIn('Example University', text)
        second.extract_text.assert_not_called()

    def test_mail_includes_all_institutions_and_escapes_html(self):
        paper = {'title': 'Test', 'authors': ['Author'], 'topic_category': 'vla',
                 'author_institutions': ['Example University', 'R&D Institute'],
                 'affiliation_source': 'https://arxiv.org/pdf/1234.56789',
                 'affiliation_source_kind': 'pdf'}
        html, _ = EmailFormatter().format_papers_to_html([paper])
        plain = EmailFormatter().generate_plain_text_email([paper])
        self.assertIn('单位：Example University；R&amp;D Institute', html)
        self.assertIn('[PDF 首页]', html)
        self.assertIn('单位: Example University；R&D Institute', plain)


class EvidenceTests(unittest.TestCase):
    def test_names_and_quotes_must_appear_in_the_source(self):
        source = '1 Example University, Department of Robotics'
        valid = json.dumps({'institutions': [{'name': 'Example University', 'evidence': source}]})
        self.assertEqual(AffiliationExtractor.validate_result(valid, source), ['Example University'])
        for item in [{'name': 'Invented University', 'evidence': source},
                     {'name': 'Example University', 'evidence': 'Invented quote'}]:
            with self.assertRaises(ValueError):
                AffiliationExtractor.validate_result(json.dumps({'institutions': [item]}), source)

    def test_empty_list_is_valid_when_no_affiliation_is_stated(self):
        self.assertEqual(AffiliationExtractor.validate_result('{"institutions": []}', 'Author Name'), [])

    def test_structured_results_are_cached_without_an_api_key(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'cache.json'
            extractor = AffiliationExtractor({}, cache)
            crawler = MagicMock()
            crawler.fetch_author_metadata.return_value = {'institutions': ['Example University'],
                'author_text': 'Example University', 'source_url': 'https://arxiv.org/html/test', 'source_kind': 'html'}
            async def run():
                first = await extractor.extract_one({'paper_id': 'test'}, crawler, None)
                second = await extractor.extract_one({'paper_id': 'test'}, crawler, None)
                return first, second
            first, second = asyncio.run(run())
            self.assertEqual(first, second)
            self.assertEqual(crawler.fetch_author_metadata.call_count, 1)
            self.assertEqual(json.loads(cache.read_text(encoding='utf-8'))['test']['author_institutions'], ['Example University'])


if __name__ == '__main__':
    unittest.main()
