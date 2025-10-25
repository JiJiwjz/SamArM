"""
DeepSeek API 客户端
负责与DeepSeek API通信，提取论文核心思想
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, Any
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
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"论文标题：{title}\n\n论文摘要：{summary}"
            }
        ]
        
        logger.debug(f"开始总结论文: {title[:50]}...")
        result = await self._call_api(messages, temperature=0.7, max_tokens=500)
        
        if result:
            logger.debug(f"论文总结完成: {title[:50]}...")
        else:
            logger.warning(f"论文总结失败: {title[:50]}...")
        
        return result
    
    async def extract_key_points(self, title: str, summary: str) -> Optional[str]:
        """
        提取论文的关键要点
        
        Args:
            title: 论文标题
            summary: 论文摘要
        
        Returns:
            关键要点或None
        """
        system_prompt = """你是一个学术论文分析专家。请提取以下论文的关键要点，
按以下格式用中文输出（每点一句话，共3-5点）：
1. 研究问题：...
2. 核心方法：...
3. 创新之处：...
4. 主要成果：...
5. 应用前景：..."""
        
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"论文标题：{title}\n\n论文摘要：{summary}"
            }
        ]
        
        logger.debug(f"开始提取关键要点: {title[:50]}...")
        result = await self._call_api(messages, temperature=0.5, max_tokens=400)
        
        return result


class DeepSeekBatchProcessor:
    """DeepSeek批量异步处理器"""
    
    def __init__(self, client: DeepSeekClient, batch_size: int = 5, 
                 max_retries: int = 3, retry_delay: float = 2.0):
        """
        初始化批处理器
        
        Args:
            client: DeepSeek客户端
            batch_size: 批处理大小
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self.client = client
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        logger.info(f"批处理器已初始化: 批大小={batch_size}, 最大重试={max_retries}")
    
    async def _process_single_paper(self, paper: Dict[str, Any], 
                                   retry_count: int = 0) -> Dict[str, Any]:
        """
        处理单篇论文（支持重试）
        
        Args:
            paper: 论文信息
            retry_count: 当前重试次数
        
        Returns:
            处理后的论文信息
        """
        try:
            # 尝试调用API总结论文
            summary_result = await self.client.summarize_paper(
                paper['title'],
                paper['summary']
            )
            
            if summary_result:
                paper['ai_summary'] = summary_result
                paper['summary_status'] = 'success'
                paper['summary_time'] = datetime.utcnow().isoformat()
                logger.info(f"✅ 总结成功: {paper['paper_id']}")
            else:
                # API调用失败，使用备选方案
                if retry_count < self.max_retries:
                    logger.warning(f"⚠️ 第{retry_count+1}次重试: {paper['paper_id']}")
                    await asyncio.sleep(self.retry_delay)
                    return await self._process_single_paper(paper, retry_count + 1)
                else:
                    # 使用论文摘要的自动缩写作为备选
                    paper['ai_summary'] = self._fallback_summary(paper['summary'])
                    paper['summary_status'] = 'fallback'
                    paper['summary_time'] = datetime.utcnow().isoformat()
                    logger.warning(f"⚠️ 使用备选方案: {paper['paper_id']}")
        
        except Exception as e:
            logger.error(f"❌ 处理失败: {paper['paper_id']}: {e}")
            paper['summary_status'] = 'error'
            paper['summary_error'] = str(e)
            paper['summary_time'] = datetime.utcnow().isoformat()
        
        return paper
    
    @staticmethod
    def _fallback_summary(summary: str, max_length: int = 300) -> str:
        """
        生成论文摘要的自动缩写（备选方案）
        
        Args:
            summary: 论文摘要
            max_length: 最大长度
        
        Returns:
            缩写后的摘要
        """
        # 简单的摘要缩写：取前几个句子
        sentences = summary.split('。')
        result = ''
        
        for sentence in sentences:
            if len(result) >= max_length:
                break
            result += sentence + '。' if sentence.strip() else ''
        
        if len(result) > max_length:
            result = result[:max_length] + '...'
        
        return result.strip()
    
    async def process_papers(self, papers: list) -> tuple:
        """
        异步批量处理论文
        
        Args:
            papers: 论文列表
        
        Returns:
            (处理成功的论文, 处理失败的论文, 统计信息)
        """
        logger.info(f"开始处理 {len(papers)} 篇论文（批大小: {self.batch_size}）...")
        
        processed_papers = []
        failed_papers = []
        
        # 分批处理
        for i in range(0, len(papers), self.batch_size):
            batch = papers[i:i + self.batch_size]
            logger.info(f"处理第 {i//self.batch_size + 1} 批 ({len(batch)} 篇)")
            
            # 并发处理当前批次
            tasks = [self._process_single_paper(paper) for paper in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"批处理中出现异常: {result}")
                elif result.get('summary_status') == 'error':
                    failed_papers.append(result)
                else:
                    processed_papers.append(result)
        
        # 统计信息
        stats = {
            'total': len(papers),
            'success': sum(1 for p in processed_papers if p.get('summary_status') == 'success'),
            'fallback': sum(1 for p in processed_papers if p.get('summary_status') == 'fallback'),
            'error': len(failed_papers)
        }
        
        logger.info(f"处理完成: 成功{stats['success']}, 备选{stats['fallback']}, 失败{stats['error']}")
        
        return processed_papers, failed_papers, stats


async def test_deepseek_client():
    """测试DeepSeek客户端"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.config import ConfigManager
    
    config = ConfigManager()
    deepseek_config = config.get_deepseek_config()
    
    # 创建客户端
    client = DeepSeekClient(
        api_key=deepseek_config.get('api_key'),
        api_url=deepseek_config.get('api_url'),
        model=deepseek_config.get('model'),
        timeout=deepseek_config.get('timeout', 30)
    )
    
    # 测试总结
    test_title = "深度学习在计算机视觉中的应用"
    test_summary = "深度学习在计算机视觉领域取得了显著进展。本文综述了卷积神经网络在图像分类、目标检测和语义分割等任务中的应用。通过大规模数据集的训练和优化，深度学习模型在多个基准数据集上取得了最先进的性能。"
    
    print("🧪 测试DeepSeek API...")
    result = await client.summarize_paper(test_title, test_summary)
    
    if result:
        print("✅ 测试成功！")
        print(f"总结结果:\n{result}")
    else:
        print("❌ 测试失败！请检查API密钥和网络连接")


if __name__ == '__main__':
    asyncio.run(test_deepseek_client())
