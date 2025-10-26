"""
论文质量多维度评估模块
使用AI对论文进行创新性、实用性、技术深度、实验完整性、影响力等多维度评估
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import json

logger = logging.getLogger(__name__)


@dataclass
class PaperQuality:
    """论文质量评估结果"""
    paper_id: str
    title: str
    
    # 五大维度评分 (1-10分)
    innovation_score: float          # 创新性
    practicality_score: float        # 实用性
    technical_depth_score: float     # 技术深度
    experimental_rigor_score: float  # 实验完整性
    impact_potential_score: float    # 影响力潜力
    
    # 综合评分
    overall_score: float             # 综合得分 (1-10)
    quality_level: str               # 质量等级: 顶级/优秀/良好/一般/较弱
    
    # 详细分析
    reasoning: str                   # AI评估理由
    strengths: List[str]             # 优点列表
    weaknesses: List[str]            # 不足列表
    
    # 元信息
    evaluation_time: str
    evaluation_status: str           # success/fallback/error
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PaperEvaluator:
    """论文质量评估器 - 使用AI进行多维度分析"""
    
    # 评估提示词模板
    EVALUATION_PROMPT = """你是一位资深的学术论文评审专家。请从以下5个维度对这篇论文进行客观、严谨的评估：

**论文信息：**
标题：{title}
摘要：{summary}

**评估维度（每个维度1-10分）：**
1. **创新性 (Innovation)**：方法是否新颖，是否有理论或技术突破
2. **实用性 (Practicality)**：解决实际问题的价值，应用潜力
3. **技术深度 (Technical Depth)**：技术复杂度，理论贡献的深度
4. **实验完整性 (Experimental Rigor)**：实验设计的严谨性，验证的充分性
5. **影响力潜力 (Impact Potential)**：对学术界或工业界的潜在影响

**评分标准：**
- 9-10分：顶级（Top）- 该维度表现极其出色，具有开创性
- 7-8分：优秀（Excellent）- 该维度表现优秀，显著超越平均水平
- 5-6分：良好（Good）- 该维度表现良好，达到发表标准
- 3-4分：一般（Fair）- 该维度表现一般，存在明显不足
- 1-2分：较弱（Weak）- 该维度表现较弱，需要大幅改进

**请严格按照以下JSON格式输出（不要添加任何其他文字）：**
{{
    "innovation_score": 数字(1-10),
    "practicality_score": 数字(1-10),
    "technical_depth_score": 数字(1-10),
    "experimental_rigor_score": 数字(1-10),
    "impact_potential_score": 数字(1-10),
    "overall_score": 数字(1-10),
    "quality_level": "顶级/优秀/良好/一般/较弱",
    "reasoning": "综合评估理由（100-200字，说明各维度得分依据）",
    "strengths": ["优点1", "优点2", "优点3"],
    "weaknesses": ["不足1", "不足2"]
}}

**注意事项：**
1. 综合评分应为5个维度分数的加权平均（创新性和影响力权重更高）
2. 评分要客观严谨，避免过高或过低，大部分论文应在4-7分之间
3. 理由要具体，避免空泛的评价
4. 优点和不足要基于摘要内容，具体可操作
"""

    def __init__(self, deepseek_config: Dict[str, Any]):
        """
        初始化评估器
        
        Args:
            deepseek_config: DeepSeek API配置
        """
        self.api_key = deepseek_config.get('api_key')
        self.api_url = deepseek_config.get('api_url', 'https://api.deepseek.com/v1')
        self.model = deepseek_config.get('model', 'deepseek-chat')
        self.timeout = deepseek_config.get('timeout', 30)
        
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置")
        
        logger.info(f"论文质量评估器已初始化: {self.model}")
    
    async def _call_deepseek_api(self, prompt: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        调用DeepSeek API进行评估
        
        Args:
            prompt: 评估提示词
            session: aiohttp会话
        
        Returns:
            API响应的JSON结果
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3,  # 降低温度以获得更一致的评分
            'max_tokens': 800
        }
        
        try:
            async with session.post(
                f"{self.api_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content'].strip()
                    
                    # 提取JSON内容
                    # 有些模型可能会在JSON前后添加文字，需要提取
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        result = json.loads(json_str)
                        return result
                    else:
                        logger.error(f"无法从响应中提取JSON: {content}")
                        return None
                else:
                    error_text = await response.text()
                    logger.error(f"DeepSeek API错误 {response.status}: {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"DeepSeek API超时")
            return None
        except Exception as e:
            logger.error(f"DeepSeek API调用异常: {e}")
            return None
    
    def _create_fallback_quality(self, paper: Dict[str, Any]) -> PaperQuality:
        """
        创建备选的质量评估（当AI不可用时）
        
        Args:
            paper: 论文信息
        
        Returns:
            备选的质量评估对象
        """
        # 基于关键词匹配给出保守评分
        relevance_score = paper.get('relevance_score', 0)
        
        # 简单映射：高相关性 -> 中等评分
        base_score = 4.0 + relevance_score * 3.0  # 4-7分范围
        
        return PaperQuality(
            paper_id=paper.get('paper_id', ''),
            title=paper.get('title', ''),
            innovation_score=base_score,
            practicality_score=base_score,
            technical_depth_score=base_score,
            experimental_rigor_score=base_score,
            impact_potential_score=base_score,
            overall_score=base_score,
            quality_level='一般',
            reasoning='AI评估暂时不可用，基于关键词匹配给出保守评分。',
            strengths=['匹配研究关键词'],
            weaknesses=['需要详细阅读原文以准确评估'],
            evaluation_time=datetime.utcnow().isoformat(),
            evaluation_status='fallback'
        )
    
    async def evaluate_single_paper(
        self, 
        paper: Dict[str, Any],
        session: aiohttp.ClientSession
    ) -> PaperQuality:
        """
        评估单篇论文
        
        Args:
            paper: 论文信息字典
            session: aiohttp会话
        
        Returns:
            质量评估对象
        """
        paper_id = paper.get('paper_id', '')
        title = paper.get('title', '')
        summary = paper.get('summary', '')
        
        logger.info(f"开始评估论文: {paper_id}")
        
        # 构建提示词
        prompt = self.EVALUATION_PROMPT.format(
            title=title,
            summary=summary[:1500]  # 限制摘要长度避免token过多
        )
        
        # 调用API
        result = await self._call_deepseek_api(prompt, session)
        
        if result:
            try:
                quality = PaperQuality(
                    paper_id=paper_id,
                    title=title,
                    innovation_score=float(result.get('innovation_score', 5)),
                    practicality_score=float(result.get('practicality_score', 5)),
                    technical_depth_score=float(result.get('technical_depth_score', 5)),
                    experimental_rigor_score=float(result.get('experimental_rigor_score', 5)),
                    impact_potential_score=float(result.get('impact_potential_score', 5)),
                    overall_score=float(result.get('overall_score', 5)),
                    quality_level=result.get('quality_level', '一般'),
                    reasoning=result.get('reasoning', ''),
                    strengths=result.get('strengths', []),
                    weaknesses=result.get('weaknesses', []),
                    evaluation_time=datetime.utcnow().isoformat(),
                    evaluation_status='success'
                )
                
                logger.info(f"✅ 论文 {paper_id} 评估成功: {quality.overall_score:.1f}/10 ({quality.quality_level})")
                return quality
                
            except Exception as e:
                logger.error(f"解析评估结果失败: {e}, result={result}")
                return self._create_fallback_quality(paper)
        else:
            logger.warning(f"论文 {paper_id} AI评估失败，使用备选方案")
            return self._create_fallback_quality(paper)
    
    async def evaluate_batch_papers(
        self,
        papers: List[Dict[str, Any]],
        batch_size: int = 3
    ) -> Tuple[List[PaperQuality], Dict[str, Any]]:
        """
        批量评估论文
        
        Args:
            papers: 论文列表
            batch_size: 并发批大小
        
        Returns:
            (评估结果列表, 统计信息)
        """
        start_time = datetime.utcnow()
        
        qualities: List[PaperQuality] = []
        stats = {
            'total': len(papers),
            'success': 0,
            'fallback': 0,
            'error': 0
        }
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(papers), batch_size):
                batch = papers[i:i + batch_size]
                batch_num = i // batch_size + 1
                
                logger.info(f"处理第 {batch_num} 批（{len(batch)} 篇）...")
                
                # 并发评估当前批次
                tasks = [self.evaluate_single_paper(paper, session) for paper in batch]
                batch_qualities = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 统计结果
                for quality in batch_qualities:
                    if isinstance(quality, Exception):
                        logger.error(f"评估异常: {quality}")
                        stats['error'] += 1
                    else:
                        qualities.append(quality)
                        if quality.evaluation_status == 'success':
                            stats['success'] += 1
                        elif quality.evaluation_status == 'fallback':
                            stats['fallback'] += 1
                        else:
                            stats['error'] += 1
                
                # 批次间延迟，避免API限流
                if i + batch_size < len(papers):
                    await asyncio.sleep(1)
        
        end_time = datetime.utcnow()
        stats['processing_time'] = (end_time - start_time).total_seconds()
        
        logger.info(
            f"批量评估完成: 总数={stats['total']}, "
            f"成功={stats['success']}, 备选={stats['fallback']}, "
            f"失败={stats['error']}, 耗时={stats['processing_time']:.2f}s"
        )
        
        return qualities, stats
