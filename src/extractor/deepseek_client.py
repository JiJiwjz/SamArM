"""
DeepSeek API 客户端
负责与DeepSeek API通信，提取论文核心思想
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """DeepSeek API 异步客户端"""
    
    def __init__(self, api_key: str, api_url: str = "https://api.deepseek.com/v1", 
                 model: str = "deepseek-chat", timeout: int = 30):
        """
        初始化DeepSeek客户端
        
        Args:
            api_key: API密钥
            api_url: API端点
            model: 模型名称
            timeout: 超时时间（秒）
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        
        logger.info(f"DeepSeek客户端已初始化: {model}")
    
    async def _call_api(self, messages: list, temperature: float = 0.7, 
                        max_tokens: int = 500) -> Optional[str]:
        """
        调用DeepSeek API（异步）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
        
        Returns:
            API响应文本或None
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        return content
                    elif response.status == 429:
                        logger.warning("API限流：429错误")
                        return None
                    elif response.status == 401:
                        logger.error("API认证失败：401错误，请检查API密钥")
                        return None
                    else:
                        error_text = await response.text()
                        logger.error(f"API返回错误 {response.status}: {error_text}")
                        return None
        
        except asyncio.TimeoutError:
            logger.warning("API请求超时")
            return None
        except Exception as e:
            logger.error(f"API调用出错: {e}")
            return None
    
    async def summarize_paper(self, title: str, summary: str, 
                             system_prompt: Optional[str] = None) -> Optional[str]:
        """
        异步总结论文
        
        Args:
            title: 论文标题
            summary: 论文摘要
            system_prompt: 系统提示词
        
        Returns:
            总结文本或None
        """
        if not system_prompt:
            system_prompt = """你是一个学术论文总结专家。请用中文总结以下论文的核心思想，
包括：1) 研究问题 2) 方法创新 3) 主要贡献 4) 实验结果。
控制在200-300字以内，语言简洁学术。"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"标题：{title}\n\n摘要：{summary}"}
        ]
        
        return await self._call_api(messages, temperature=0.5, max_tokens=500)
    
    async def evaluate_paper_quality(self, title: str, summary: str, 
                                     authors: list = None) -> Optional[Dict[str, Any]]:
        """
        🆕 评估论文水平
        
        Args:
            title: 论文标题
            summary: 论文摘要
            authors: 作者列表（可选）
        
        Returns:
            评估结果字典，包含：
            - quality_score: 质量评分 (1-10)
            - quality_level: 水平等级 (顶级/优秀/良好/一般/较弱)
            - reasoning: 评估理由
        """
        authors_info = f"作者：{', '.join(authors[:3])}" if authors else ""
        
        system_prompt = """你是一个资深的学术论文评审专家。请根据论文的标题和摘要，评估其学术水平。

评估维度：
1. 创新性：研究问题和方法是否有创新
2. 技术深度：方法是否有技术难度和深度
3. 实用价值：研究成果的应用价值
4. 实验完整性：实验设计是否完整充分

请以JSON格式返回评估结果：
{
  "quality_score": 8,
  "quality_level": "优秀",
  "reasoning": "简要说明评分理由（50字以内）"
}

评分标准：
- 9-10分：顶级（顶会/顶刊水平，创新性强，影响力大）
- 7-8分：优秀（方法新颖，实验充分，有较好贡献）
- 5-6分：良好（有一定创新，实验合理）
- 3-4分：一般（创新有限，实验基础）
- 1-2分：较弱（缺乏创新或实验不足）"""
        
        user_content = f"""请评估以下论文：

标题：{title}

{authors_info}

摘要：{summary}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        response = await self._call_api(messages, temperature=0.3, max_tokens=300)
        
        if not response:
            return None
        
        try:
            # 提取JSON内容
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # 验证字段
                if 'quality_score' in result and 'quality_level' in result:
                    # 确保评分在1-10范围内
                    result['quality_score'] = max(1, min(10, int(result['quality_score'])))
                    return result
            
            logger.warning(f"无法解析论文评估结果: {response}")
            return None
            
        except Exception as e:
            logger.error(f"解析论文评估JSON失败: {e}")
            return None


class DeepSeekBatchProcessor:
    """DeepSeek批处理器"""
    
    def __init__(self, client: DeepSeekClient, batch_size: int = 3, delay: float = 0.5):
        """
        初始化批处理器
        
        Args:
            client: DeepSeek客户端
            batch_size: 批处理大小
            delay: 批次间延迟（秒）
        """
        self.client = client
        self.batch_size = batch_size
        self.delay = delay
    
    async def process_papers_with_evaluation(self, papers: list, 
                                            system_prompt: Optional[str] = None) -> Tuple[list, list]:
        """
        🆕 批量处理论文（包含总结和评估）
        
        Args:
            papers: 论文列表
            system_prompt: 系统提示词
        
        Returns:
            (总结结果列表, 评估结果列表)
        """
        summaries = []
        evaluations = []
        total = len(papers)
        
        for i in range(0, total, self.batch_size):
            batch = papers[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            logger.info(f"正在处理第 {batch_num}/{total_batches} 批...")
            
            # 并发执行总结和评估
            tasks = []
            for paper in batch:
                # 总结任务
                summary_task = self.client.summarize_paper(
                    paper.get('title', ''),
                    paper.get('summary', ''),
                    system_prompt
                )
                # 评估任务
                eval_task = self.client.evaluate_paper_quality(
                    paper.get('title', ''),
                    paper.get('summary', ''),
                    paper.get('authors', [])
                )
                tasks.append((summary_task, eval_task, paper))
            
            # 等待所有任务完成
            batch_results = await asyncio.gather(
                *[asyncio.gather(s, e) for s, e, p in tasks],
                return_exceptions=True
            )
            
            # 处理结果
            for (summary_result, eval_result), (_, _, paper) in zip(batch_results, tasks):
                paper_id = paper.get('paper_id', 'unknown')
                
                # 处理总结结果
                if isinstance(summary_result, Exception):
                    logger.error(f"总结失败 {paper_id}: {summary_result}")
                    summaries.append((paper, None))
                else:
                    summaries.append((paper, summary_result))
                
                # 处理评估结果
                if isinstance(eval_result, Exception):
                    logger.error(f"评估失败 {paper_id}: {eval_result}")
                    evaluations.append((paper, None))
                else:
                    evaluations.append((paper, eval_result))
            
            # 批次间延迟
            if i + self.batch_size < total:
                await asyncio.sleep(self.delay)
        
        return summaries, evaluations
