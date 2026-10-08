"""
arxiv论文爬取模块
负责从arxiv检索、爬取符合条件的论文信息
"""

import arxiv
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time
import io
import re

from src.extractor.affiliation_extractor import unique_institutions

logger = logging.getLogger(__name__)


class TimeoutAdapter(requests.adapters.HTTPAdapter):
    """arxiv 2.1.0 has no request timeout; bound network waits."""
    def __init__(self, timeout=30):
        super().__init__(max_retries=2)
        self.timeout = timeout

    def send(self, request, **kwargs):
        if kwargs.get('timeout') is None:
            kwargs['timeout'] = (10, self.timeout)
        return super().send(request, **kwargs)


@dataclass
class Paper:
    """论文数据结构"""
    paper_id: str              # arxiv ID
    title: str                 # 论文标题
    authors: List[str]         # 作者列表
    summary: str               # 摘要
    published: str             # 发布日期
    updated: str               # 更新日期
    categories: str            # 分类
    pdf_url: str               # PDF链接
    arxiv_url: str             # arxiv链接
    fetch_time: str            # 获取时间
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class ArxivCrawler:
    """arxiv爬虫 - 从arxiv获取论文"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬虫
        
        Args:
            config: 配置字典，包含关键词、分类等信息
        """
        self.config = config
        self.keywords = config.get('keywords', [])
        self.categories = config.get('categories', [])
        self.max_results = config.get('max_results', 50)
        self.sort_by = config.get('sort_by', 'submittedDate')
        self.search_mode = 'or'  # 默认使用OR逻辑
        self.last_error = None
        self._html_cache = {}
        
        # 初始化客户端
        self.client = arxiv.Client(
            page_size=min(self.max_results, 100),
            delay_seconds=3,
            num_retries=3
        )
        self.client._session.mount('https://', TimeoutAdapter(config.get('timeout', 30)))
        self.client._session.mount('http://', TimeoutAdapter(config.get('timeout', 30)))
        
        logger.info(f"arxiv爬虫已初始化。关键词: {self.keywords}, 分类: {self.categories}")
    
    def set_search_mode(self, mode: str = 'or'):
        """
        设置搜索模式
        
        Args:
            mode: 搜索模式
                - 'or': 使用OR逻辑（宽松匹配）
                - 'and': 使用AND逻辑（严格匹配）
                - 'keyword_only': 仅搜索关键词，忽略分类
                - 'category_only': 仅搜索分类，忽略关键词
        """
        self.search_mode = mode.lower()
        logger.info(f"搜索模式已设置为: {self.search_mode}")
    
    def build_search_query(self) -> str:
        """
        构建arxiv搜索查询语句
        支持多种搜索模式
        
        Returns:
            查询语句
        """
        mode = self.search_mode
        
        if mode == 'keyword_only':
            return self._build_keyword_query()
        elif mode == 'category_only':
            return self._build_category_query()
        elif mode == 'and':
            return self._build_and_query()
        else:  # 默认 'or'
            return self._build_or_query()
    
    def _build_or_query(self) -> str:
        """使用OR逻辑构建查询（宽松匹配）"""
        query_parts = []
        
        for keyword in self.keywords:
            if keyword.strip():
                query_parts.append(f'all:"{keyword.strip()}"')
        
        for category in self.categories:
            if category.strip():
                query_parts.append(f"cat:{category}")
        
        if not query_parts:
            query_parts.append("cat:cs.CV")
        
        query = " OR ".join(query_parts)
        if len(query_parts) > 1:
            query = f"({query})"
        
        logger.debug(f"OR查询: {query}")
        return query
    
    def _build_and_query(self) -> str:
        """使用AND逻辑构建查询（严格匹配）"""
        keyword_part = " OR ".join([f'all:"{k.strip()}"' for k in self.keywords if k.strip()])
        category_part = " OR ".join([f"cat:{c}" for c in self.categories if c.strip()])
        
        if keyword_part and category_part:
            query = f"({keyword_part}) AND ({category_part})"
        elif keyword_part:
            query = keyword_part
        elif category_part:
            query = category_part
        else:
            query = "cat:cs.CV"
        
        logger.debug(f"AND查询: {query}")
        return query
    
    def _build_keyword_query(self) -> str:
        """仅使用关键词查询"""
        query_parts = [f'all:"{k.strip()}"' for k in self.keywords if k.strip()]
        if not query_parts:
            query_parts.append("cat:cs.CV")
        
        query = " OR ".join(query_parts)
        if len(query_parts) > 1:
            query = f"({query})"
        
        logger.debug(f"关键词查询: {query}")
        return query
    
    def _build_category_query(self) -> str:
        """仅使用分类查询"""
        query_parts = [f"cat:{c}" for c in self.categories if c.strip()]
        if not query_parts:
            query_parts.append("cat:cs.CV")
        
        query = " OR ".join(query_parts)
        if len(query_parts) > 1:
            query = f"({query})"
        
        logger.debug(f"分类查询: {query}")
        return query
    
    def fetch_papers(self, days_back: int = 1) -> List[Paper]:
        """
        从arxiv获取论文
        
        Args:
            days_back: 向后查找的天数（默认1天，即当天）
        
        Returns:
            论文列表
        """
        query = self.build_search_query()
        if self.config.get('robotics_only', False):
            context = ('cat:cs.RO OR all:robot OR all:robots OR all:robotic OR '
                       'all:manipulation OR all:dexterous OR all:grasping OR all:LIBERO OR all:CALVIN')
            query = f'({query}) AND ({context})'
        self.last_error = None
        papers = []
        
        try:
            logger.info(f"开始从arxiv查询论文（查找过去{days_back}天）...")
            logger.info(f"搜索查询: {query}")
            
            # 排序方式映射
            sort_criterion_map = {
                'submittedDate': arxiv.SortCriterion.SubmittedDate,
                'relevance': arxiv.SortCriterion.Relevance,
                'lastUpdatedDate': arxiv.SortCriterion.LastUpdatedDate,
            }
            sort_by = sort_criterion_map.get(self.sort_by, arxiv.SortCriterion.SubmittedDate)
            
            now = datetime.now(timezone.utc)
            cutoff_date = now - timedelta(days=days_back)
            query = (f'({query}) AND submittedDate:'
                     f'[{cutoff_date.strftime("%Y%m%d%H%M")} TO {now.strftime("%Y%m%d%H%M")}]')
            # Apply the date range on the server before max_results truncation.
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=sort_by,
                sort_order=arxiv.SortOrder.Descending
            )
            
            # 计算时间范围（基于系统时钟的UTC时间，AI不参与日期计算）
            logger.info(
                f"检索时间窗口（系统时钟实时计算）: "
                f"{cutoff_date.strftime('%Y-%m-%d %H:%M')} UTC 至 {now.strftime('%Y-%m-%d %H:%M')} UTC，"
                f"即北京时间 {(cutoff_date + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')} 至 "
                f"{(now + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')}"
            )
            
            # 获取论文
            count = 0
            for entry in self.client.results(search):
                # 检查论文发布日期（arxiv返回的时间自带UTC时区）
                published_date = entry.published
                
                if published_date < cutoff_date:
                    logger.debug(f"论文 {entry.entry_id} 发布于{published_date}，已超出时间范围")
                    if self.sort_by == 'submittedDate':
                        break
                    continue
                
                paper = self._parse_paper(entry)
                papers.append(paper)
                count += 1
                
                logger.debug(f"获取论文: {paper.title[:50]}...")
                
                # The client already spaces API page requests by 3 seconds.
            
            logger.info(f"成功获取 {count} 篇论文")
            return papers
        
        except Exception as e:
            self.last_error = str(e)
            logger.error(f"从arxiv获取论文时出错: {e}", exc_info=True)
            return []
    
    def _parse_paper(self, entry) -> Paper:
        """
        解析arxiv条目为Paper对象
        
        Args:
            entry: arxiv API返回的条目
        
        Returns:
            Paper对象
        """
        # 提取作者名称
        authors = [author.name for author in entry.authors]
        
        # 提取分类
        categories = ", ".join(entry.categories)
        
        # 构造URLs
        paper_id = entry.entry_id.split('/abs/')[-1]
        arxiv_url = f"https://arxiv.org/abs/{paper_id}"
        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        
        paper = Paper(
            paper_id=paper_id,
            title=entry.title,
            authors=authors,
            summary=entry.summary,
            published=entry.published.isoformat(),
            updated=entry.updated.isoformat(),
            categories=categories,
            pdf_url=pdf_url,
            arxiv_url=arxiv_url,
            fetch_time=datetime.utcnow().isoformat()
        )
        
        return paper
    
    def fetch_papers_by_keywords(self, keywords: List[str], days_back: int = 1) -> List[Paper]:
        """
        按特定关键词搜索论文
        
        Args:
            keywords: 关键词列表
            days_back: 向后查找的天数
        
        Returns:
            论文列表
        """
        # 临时替换关键词
        original_keywords = self.keywords
        self.keywords = keywords
        
        try:
            papers = self.fetch_papers(days_back)
            return papers
        finally:
            # 恢复原始关键词
            self.keywords = original_keywords
    
    def _get_html(self, paper_id, timeout=3):
        if not paper_id:
            return None, ''
        if paper_id in self._html_cache:
            return self._html_cache[paper_id]
        # Keep the exact version so later author changes cannot alter affiliations.
        urls = [f'https://arxiv.org/html/{paper_id}']
        result = (None, '')
        for url in urls:
            try:
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    result = (BeautifulSoup(response.text, 'html.parser'), url)
                    break
            except requests.RequestException as error:
                logger.debug('HTML unavailable for %s: %s', paper_id, error)
        self._html_cache[paper_id] = result
        return result

    @staticmethod
    def parse_author_metadata(soup):
        institutions = [node.get('content', '') for node in
                        soup.select('meta[name="citation_author_institution"]')]
        authors = soup.select_one('.ltx_authors')
        if authors:
            for node in authors.select('.ltx_role_affiliation, .ltx_affiliation'):
                text = node.get_text(' ', strip=True)
                text = re.sub(r'^Affiliation\s*:\s*', '', text, flags=re.I)
                text = re.split(r'Project\s+page|https?://|\S+@\S+', text, flags=re.I)[0].strip()
                if text:
                    institutions.append(text)
            institution_hint = re.compile(
                r'University|Institute|College|School|Academy|Laborator|Research|Center|Centre|'
                r'Google|DeepMind|Microsoft|NVIDIA|Physical Intelligence|Toyota|Samsung|'
                r'Amazon|Apple|Meta|Tencent|Alibaba|ByteDance|Huawei|Bosch', re.I)
            for marker in authors.find_all('sup'):
                chunks = []
                for sibling in marker.next_siblings:
                    if getattr(sibling, 'name', None) in ('sup', 'br'):
                        break
                    chunks.append(sibling.get_text(' ', strip=True) if hasattr(sibling, 'get_text') else str(sibling))
                text = ' '.join(chunks).strip()
                text = re.split(r'Project\s+page|https?://|\S+@\S+', text, flags=re.I)[0].strip()
                if text and len(text) <= 250 and institution_hint.search(text):
                    institutions.append(text)
        institutions = unique_institutions(v for v in institutions if v and '@' not in v)
        author_text = authors.get_text(' ', strip=True) if authors else ''
        author_text = re.sub(r'\S+@\S+', '', author_text)[:12000]
        return institutions, author_text

    @staticmethod
    def extract_pdf_author_text(data):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if not reader.pages:
            return ''
        return (reader.pages[0].extract_text(extraction_mode='layout') or '')[:16000]

    def fetch_author_metadata(self, paper_id, timeout=8, max_pdf_mb=15):
        soup, html_url = self._get_html(paper_id, timeout=min(timeout, 3))
        html_metadata = {}
        if soup:
            institutions, author_text = self.parse_author_metadata(soup)
            if institutions or author_text:
                html_metadata = {'institutions': institutions, 'author_text': author_text,
                                 'source_url': html_url, 'source_kind': 'html'}
                if institutions:
                    return html_metadata
        pdf_url = f'https://arxiv.org/pdf/{paper_id}'
        try:
            max_bytes = int(max_pdf_mb * 1024 * 1024)
            start = time.monotonic()
            with requests.get(pdf_url, timeout=(5, timeout), stream=True) as response:
                response.raise_for_status()
                if int(response.headers.get('Content-Length', 0)) > max_bytes:
                    return html_metadata
                data = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    data.extend(chunk)
                    if len(data) > max_bytes or time.monotonic() - start > timeout:
                        return html_metadata
            if not data.lstrip().startswith(b'%PDF-'):
                return html_metadata
            text = self.extract_pdf_author_text(data)
            return {'institutions': [], 'author_text': text,
                    'source_url': pdf_url, 'source_kind': 'pdf'}
        except Exception as error:
            logger.debug('PDF author metadata unavailable for %s: %s', paper_id, error)
            return html_metadata

    def fetch_overview_image(self, paper_id: str, timeout: int = 3) -> Optional[str]:
        """Reuse the HTML page fetched for author metadata."""
        soup, page_url = self._get_html(paper_id, timeout)
        if not soup:
            return None
        for figure in soup.find_all('figure'):
            image = figure.find('img')
            if not image or not image.get('src'):
                continue
            try:
                width = int(image.get('width', 0) or 0)
                if 0 < width < 200:
                    continue
            except (ValueError, TypeError):
                pass
            return urljoin(page_url, image['src'])
        return None

    def download_paper_info(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        下载单篇论文的详细信息
        
        Args:
            paper_id: 论文ID
        
        Returns:
            论文信息字典或None
        """
        try:
            search = arxiv.Search(id_list=[paper_id])
            for entry in self.client.results(search):
                paper = self._parse_paper(entry)
                return paper.to_dict()
            return None
        except Exception as e:
            logger.error(f"下载论文 {paper_id} 信息时出错: {e}")
            return None


def main():
    """测试爬虫"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.config import ConfigManager
    
    config_manager = ConfigManager()
    arxiv_config = config_manager.get_arxiv_config()
    
    # 创建爬虫实例
    crawler = ArxivCrawler(arxiv_config)
    
    # 获取论文
    papers = crawler.fetch_papers(days_back=1)
    
    # 显示结果
    for i, paper in enumerate(papers[:5], 1):
        print(f"\n【论文 {i}】")
        print(f"标题: {paper.title}")
        print(f"作者: {', '.join(paper.authors[:3])}...")
        print(f"发布时间: {paper.published}")
        print(f"链接: {paper.arxiv_url}")
        print(f"摘要: {paper.summary[:200]}...")


if __name__ == '__main__':
    main()
