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
    
    # 🆕 论文质量评估
    quality_score: Optional[int] = None     # 质量评分 1-10
    quality_level: Optional[str] = None     # 质量等级
    quality_reasoning: Optional[str] = None # 评估理由
    
    extraction_status: str = 'unknown'      # success|fallback|error
    extraction_error: Optional[str] = None  # 错误信息
    extraction_time: str = ''               # 提取时间
    
    # 原论文信息
    published: str = ''
    arxiv_url: str = ''
    
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
    
    def _fallback_summary(self, original_summary: str, max_len: int = 300) -> str:
        """备选总结方案：截断原始摘要"""
        if len(original_summary) <= max_len:
            return original_summary
        return original_summary[:max_len] + "..."
    
    async def extract_single_paper(self, paper: Dict[str, Any]) -> ExtractedIdea:
        """
        异步提取单篇论文的核心思想（包含评估）
        
        Args:
            paper: 论文信息字典
        
        Returns:
            提取的思想对象
        """
        paper_id = paper.get('paper_id', 'unknown')
        
        try:
            # 并发执行总结和评估
            summary_task = self.client.summarize_paper(
                paper.get('title', ''),
                paper.get('summary', ''),
                self.system_prompt
            )
            
            eval_task = self.client.evaluate_paper_quality(
                paper.get('title', ''),
                paper.get('summary', ''),
                paper.get('authors', [])
            )
            
            ai_summary, eval_result = await asyncio.gather(summary_task, eval_task)
            
            # 处理总结结果
            if ai_summary:
                extraction_status = 'success'
                extraction_error = None
                logger.info(f"✅ 思想提取成功: {paper_id}")
            else:
                ai_summary = self._fallback_summary(paper.get('summary', ''))
                extraction_status = 'fallback'
                extraction_error = 'API调用失败，使用备选方案'
                logger.warning(f"⚠️  API失败，使用备选方案: {paper_id}")
            
            # 处理评估结果
            if eval_result:
                quality_score = eval_result.get('quality_score')
                quality_level = eval_result.get('quality_level')
                quality_reasoning = eval_result.get('reasoning')
                logger.info(f"📊 论文评估: {paper_id} - {quality_level} ({quality_score}/10)")
            else:
                quality_score = None
                quality_level = None
                quality_reasoning = None
                logger.warning(f"⚠️  论文评估失败: {paper_id}")
            
        except Exception as e:
            logger.error(f"❌ 提取失败 {paper_id}: {e}")
            ai_summary = self._fallback_summary(paper.get('summary', ''))
            extraction_status = 'error'
            extraction_error = str(e)
            quality_score = None
            quality_level = None
            quality_reasoning = None
        
        return ExtractedIdea(
            paper_id=paper_id,
            title=paper.get('title', ''),
            authors=paper.get('authors', []),
            summary=paper.get('summary', ''),
            ai_summary=ai_summary,
            key_points=None,
            quality_score=quality_score,
            quality_level=quality_level,
            quality_reasoning=quality_reasoning,
            extraction_status=extraction_status,
            extraction_error=extraction_error,
            extraction_time=datetime.now().isoformat(),
            published=paper.get('published', ''),
            arxiv_url=paper.get('arxiv_url', '')
        )
    
    async def extract_batch_papers(self, papers: List[Dict[str, Any]], 
                                   batch_size: int = 3) -> Tuple[List[ExtractedIdea], Dict[str, Any]]:
        """
        批量提取论文思想（异步，带评估）
        
        ⚠️ 方法名必须是 extract_batch_papers 以兼容 daily_job.py
        
        Args:
            papers: 论文列表
            batch_size: 批处理大小
        
        Returns:
            (提取的思想列表, 统计信息字典)
        """
        start_time = datetime.now()
        processor = DeepSeekBatchProcessor(self.client, batch_size=batch_size)
        
        summaries, evaluations = await processor.process_papers_with_evaluation(
            papers, self.system_prompt
        )
        
        results = []
        success_count = 0
        fallback_count = 0
        error_count = 0
        
        for (paper, ai_summary), (_, eval_result) in zip(summaries, evaluations):
            paper_id = paper.get('paper_id', 'unknown')
            
            # 处理总结
            if ai_summary:
                extraction_status = 'success'
                extraction_error = None
                success_count += 1
            else:
                ai_summary = self._fallback_summary(paper.get('summary', ''))
                extraction_status = 'fallback'
                extraction_error = 'API调用失败'
                fallback_count += 1
            
            # 处理评估
            if eval_result:
                quality_score = eval_result.get('quality_score')
                quality_level = eval_result.get('quality_level')
                quality_reasoning = eval_result.get('reasoning')
            else:
                quality_score = None
                quality_level = None
                quality_reasoning = None
            
            results.append(ExtractedIdea(
                paper_id=paper_id,
                title=paper.get('title', ''),
                authors=paper.get('authors', []),
                summary=paper.get('summary', ''),
                ai_summary=ai_summary,
                key_points=None,
                quality_score=quality_score,
                quality_level=quality_level,
                quality_reasoning=quality_reasoning,
                extraction_status=extraction_status,
                extraction_error=extraction_error,
                extraction_time=datetime.now().isoformat(),
                published=paper.get('published', ''),
                arxiv_url=paper.get('arxiv_url', '')
            ))
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        stats = {
            'success': success_count,
            'fallback': fallback_count,
            'error': error_count,
            'total': len(results),
            'processing_time': processing_time
        }
        
        logger.info(f"批量提取完成：共 {len(results)} 篇 (成功:{success_count} 备选:{fallback_count} 失败:{error_count})")
        return results, stats
