"""
论文核心思想提取模块
负责对论文进行AI总结和思想提取
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from .deepseek_client import DeepSeekClient, DeepSeekBatchProcessor

logger = logging.getLogger(__name__)


@dataclass
class ExtractedIdea:
    """提取的论文思想"""
    paper_id: str
    title: str
    authors: List[str]
    summary: str                    # 原始摘要
    ai_summary: str                 # AI生成的总结
    key_points: Optional[str]       # 关键要点
    
    extraction_status: str          # success|fallback|error
    extraction_error: Optional[str] # 错误信息
    extraction_time: str            # 提取时间
    
    # 原论文信息
    published: str
    arxiv_url: str
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class IdeaExtractor:
    """论文思想提取器"""
    
    def __init__(self, deepseek_config: Dict[str, Any]):
        """
        初始化思想提取器
        
        Args:
            deepseek_config: DeepSeek配置字典
        """
        api_key = deepseek_config.get('api_key')
        if not api_key:
            raise ValueError("DeepSeek API密钥未配置！")
        
        self.client = DeepSeekClient(
            api_key=api_key,
            api_url=deepseek_config.get('api_url', 'https://api.deepseek.com/v1'),
            model=deepseek_config.get('model', 'deepseek-chat'),
            timeout=deepseek_config.get('timeout', 30)
        )
        
        self.system_prompt = deepseek_config.get('system_prompt', 
            """你是一个学术论文总结专家。请用中文总结以下论文的核心思想，
包括：1) 研究问题 2) 方法创新 3) 主要贡献 4) 实验结果。
控制在200-300字以内，语言简洁学术。""")
        
        logger.info("论文思想提取器已初始化")
    
    async def extract_single_paper(self, paper: Dict[str, Any]) -> ExtractedIdea:
        """
        异步提取单篇论文的核心思想
        
        Args:
            paper: 论文信息字典
        
        Returns:
            提取的思想对象
        """
        paper_id = paper.get('paper_id', 'unknown')
        
        try:
            # 调用API总结论文
            ai_summary = await self.client.summarize_paper(
                paper.get('title', ''),
                paper.get('summary', ''),
                self.system_prompt
            )
            
            if ai_summary:
                extraction_status = 'success'
                extraction_error = None
                logger.info(f"✅ 思想提取成功: {paper_id}")
            else:
                # API失败，使用备选方案
                ai_summary = self._fallback_summary(paper.get('summary', ''))
                extraction_status = 'fallback'
                extraction_error = 'API调用失败，使用备选方案'
                logger.warning(f"⚠️ 使用备选方案: {paper_id}")
            
            # 创建提取结果
            idea = ExtractedIdea(
                paper_id=paper_id,
                title=paper.get('title', ''),
                authors=paper.get('authors', []),
                summary=paper.get('summary', ''),
                ai_summary=ai_summary,
                key_points=None,  # 可选，暂不提取
                extraction_status=extraction_status,
                extraction_error=extraction_error,
                extraction_time=datetime.utcnow().isoformat(),
                published=paper.get('published', ''),
                arxiv_url=paper.get('arxiv_url', '')
            )
            
            return idea
        
        except Exception as e:
            logger.error(f"❌ 思想提取失败: {paper_id}: {e}")
            
            idea = ExtractedIdea(
                paper_id=paper_id,
                title=paper.get('title', ''),
                authors=paper.get('authors', []),
                summary=paper.get('summary', ''),
                ai_summary=self._fallback_summary(paper.get('summary', '')),
                key_points=None,
                extraction_status='error',
                extraction_error=str(e),
                extraction_time=datetime.utcnow().isoformat(),
                published=paper.get('published', ''),
                arxiv_url=paper.get('arxiv_url', '')
            )
            
            return idea
    
    @staticmethod
    def _fallback_summary(summary: str, max_length: int = 300) -> str:
        """
        备选方案：生成论文摘要的自动缩写
        
        Args:
            summary: 论文摘要
            max_length: 最大长度
        
        Returns:
            缩写后的摘要
        """
        if not summary:
            return "论文摘要缺失"
        
        # 按句号分割
        sentences = summary.split('。')
        result = ''
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(result) + len(sentence) + 1 <= max_length:
                result += sentence + '。'
            else:
                break
        
        if not result:
            # 如果没有句号，直接截断
            result = summary[:max_length]
            if len(summary) > max_length:
                result += '...'
        
        return result.strip()
    
    async def extract_batch_papers(self, papers: List[Dict[str, Any]], 
                                   batch_size: int = 5) -> Tuple[List[ExtractedIdea], Dict[str, Any]]:
        """
        异步批量提取论文思想
        
        Args:
            papers: 论文列表
            batch_size: 批处理大小
        
        Returns:
            (提取结果列表, 统计信息)
        """
        logger.info(f"开始批量提取 {len(papers)} 篇论文的思想（批大小: {batch_size}）...")
        
        extracted_ideas = []
        stats = {
            'total': len(papers),
            'success': 0,
            'fallback': 0,
            'error': 0,
            'processing_time': 0
        }
        
        start_time = datetime.utcnow()
        
        # 分批异步处理
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            logger.info(f"处理第 {batch_num} 批 ({len(batch)} 篇)...")
            
            # 并发处理当前批次
            tasks = [self.extract_single_paper(paper) for paper in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"处理出现异常: {result}")
                    stats['error'] += 1
                else:
                    extracted_ideas.append(result)
                    if result.extraction_status == 'success':
                        stats['success'] += 1
                    elif result.extraction_status == 'fallback':
                        stats['fallback'] += 1
                    else:
                        stats['error'] += 1
        
        end_time = datetime.utcnow()
        stats['processing_time'] = (end_time - start_time).total_seconds()
        
        logger.info(f"批量提取完成: 成功{stats['success']}, 备选{stats['fallback']}, 失败{stats['error']}, "
                   f"耗时{stats['processing_time']:.2f}秒")
        
        return extracted_ideas, stats


def main():
    """测试思想提取功能"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.crawler import ArxivCrawler
    from src.config import ConfigManager
    from src.filter import PaperFilter
    
    async def run():
        # 获取配置
        config_manager = ConfigManager()
        arxiv_config = config_manager.get_arxiv_config()
        deepseek_config = config_manager.get_deepseek_config()
        
        # 爬取论文
        crawler = ArxivCrawler(arxiv_config)
        papers = crawler.fetch_papers(days_back=3)
        papers_dict = [p.to_dict() for p in papers]
        
        # 筛选论文
        filter_obj = PaperFilter()
        filtered_papers, _ = filter_obj.filter_papers(papers_dict)
        
        # 只取前3篇进行测试
        test_papers = [p.to_dict() for p in filtered_papers[:3]]
        
        print(f"\n📚 准备提取 {len(test_papers)} 篇论文的核心思想...\n")
        
        # 创建提取器
        extractor = IdeaExtractor(deepseek_config)
        
        # 提取论文思想
        extracted_ideas, stats = await extractor.extract_batch_papers(test_papers, batch_size=2)
        
        # 显示结果
        print(f"\n{'='*70}")
        print(f"📊 提取统计: 成功{stats['success']}, 备选{stats['fallback']}, 失败{stats['error']}")
        print(f"⏱️  耗时: {stats['processing_time']:.2f}秒")
        print(f"{'='*70}\n")
        
        for i, idea in enumerate(extracted_ideas, 1):
            print(f"【论文 {i}】")
            print(f"标题: {idea.title}")
            print(f"作者: {', '.join(idea.authors[:2])}...")
            print(f"状态: {idea.extraction_status}")
            print(f"\n🤖 AI总结:")
            print(f"{idea.ai_summary}\n")
            print(f"链接: {idea.arxiv_url}\n")
            print("-" * 70 + "\n")
    
    asyncio.run(run())


if __name__ == '__main__':
    main()
