"""
邮件模板
定义HTML邮件的样式和结构
"""

from datetime import datetime


class EmailTemplate:
    """邮件模板类"""
    
    @staticmethod
    def get_header(date_str: str, total_papers: int, topic_stats: dict = None) -> str:
        """
        生成邮件头部
        
        Args:
            date_str: 日期字符串
            total_papers: 论文总数
            topic_stats: 主题统计字典
        
        Returns:
            HTML头部
        """
        topic_html = ""
        if topic_stats:
            topic_html = "<tr><td style='padding: 10px 0;'><strong>📊 主题分布：</strong> "
            for topic, count in sorted(topic_stats.items(), key=lambda x: x[1], reverse=True):
                topic_html += f"{topic}: {count}篇 | "
            topic_html = topic_html.rstrip(" | ") + "</td></tr>"
        
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>【Arxiv论文日报】{date_str}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .info-box {{
            background-color: #f0f4ff;
            border-left: 4px solid #667eea;
            padding: 15px 20px;
            margin: 20px 30px;
            font-size: 13px;
            line-height: 1.8;
        }}
        
        .info-box strong {{
            color: #667eea;
        }}
        
        .content {{
            padding: 0 30px 30px 30px;
        }}
        
        .paper-card {{
            background-color: #fafafa;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
        }}
        
        .paper-card:hover {{
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            border-color: #667eea;
        }}
        
        .paper-number {{
            display: inline-block;
            background-color: #667eea;
            color: white;
            width: 28px;
            height: 28px;
            border-radius: 50%;
            text-align: center;
            line-height: 28px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .paper-title {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin: 10px 0;
            line-height: 1.4;
        }}
        
        .paper-title a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        .paper-title a:hover {{
            text-decoration: underline;
        }}
        
        .paper-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            font-size: 12px;
            color: #666;
            margin: 10px 0;
        }}
        
        .paper-meta span {{
            display: flex;
            align-items: center;
        }}
        
        .paper-meta strong {{
            color: #333;
            margin-right: 5px;
        }}
        
        .paper-authors {{
            font-size: 13px;
            color: #555;
            margin: 8px 0;
            font-style: italic;
        }}
        
        .paper-topic {{
            display: inline-block;
            background-color: #e8f0fe;
            color: #667eea;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin: 5px 5px 5px 0;
        }}
        
        .paper-score {{
            display: inline-block;
            background-color: #fff3e0;
            color: #f57c00;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin: 5px 5px 5px 0;
        }}
        
        .quality-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            margin: 5px 5px 5px 0;
        }}
        
        .quality-top {{
            background-color: #fff3e0;
            color: #e65100;
        }}
        
        .quality-excellent {{
            background-color: #e8f5e9;
            color: #2e7d32;
        }}
        
        .quality-good {{
            background-color: #e3f2fd;
            color: #1565c0;
        }}
        
        .quality-normal {{
            background-color: #f3e5f5;
            color: #6a1b9a;
        }}
        
        .quality-weak {{
            background-color: #fafafa;
            color: #757575;
        }}
        
        .paper-summary {{
            background-color: #ffffff;
            border-left: 3px solid #667eea;
            padding: 12px 15px;
            margin: 12px 0;
            font-size: 13px;
            line-height: 1.7;
            color: #555;
        }}
        
        .quality-reasoning {{
            background-color: #fffef7;
            border-left: 3px solid #ffa726;
            padding: 10px 15px;
            margin: 12px 0;
            font-size: 12px;
            line-height: 1.6;
            color: #666;
            font-style: italic;
        }}
        
        .paper-keywords {{
            font-size: 12px;
            color: #999;
            margin: 10px 0;
        }}
        
        .paper-keywords strong {{
            color: #666;
        }}
        
        .paper-link {{
            display: inline-block;
            background-color: #667eea;
            color: white;
            padding: 6px 14px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
            margin-top: 10px;
            transition: background-color 0.3s;
        }}
        
        .paper-link:hover {{
            background-color: #764ba2;
        }}
        
        .footer {{
            background-color: #f5f5f5;
            border-top: 1px solid #e0e0e0;
            padding: 20px 30px;
            font-size: 12px;
            color: #999;
            text-align: center;
        }}
        
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
        
        .divider {{
            height: 1px;
            background-color: #e0e0e0;
            margin: 20px 0;
        }}
        
        @media only screen and (max-width: 600px) {{
            .container {{
                width: 100%;
            }}
            
            .header {{
                padding: 30px 20px;
            }}
            
            .header h1 {{
                font-size: 22px;
            }}
            
            .content {{
                padding: 0 20px 20px 20px;
            }}
            
            .info-box {{
                margin: 15px 20px;
                padding: 12px 15px;
                font-size: 12px;
            }}
            
            .paper-card {{
                padding: 15px;
                margin-bottom: 15px;
            }}
            
            .paper-meta {{
                gap: 10px;
                font-size: 11px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 Arxiv论文日报</h1>
            <p>{date_str}</p>
        </div>
        
        <div class="info-box">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 5px 0;"><strong>📊 总论文数：</strong> {total_papers} 篇</td></tr>
                {topic_html}
            </table>
        </div>
        
        <div class="content">
"""

    @staticmethod
    def get_paper_card(index: int, paper: dict) -> str:
        """
        生成单篇论文的卡片HTML
        
        Args:
            index: 论文序号
            paper: 论文信息字典（包含AI总结和评估）
        
        Returns:
            HTML卡片
        """
        # 提取信息
        title = paper.get('title', '未知标题')
        authors = paper.get('authors', [])
        published = paper.get('published', '')[:10]
        topic = paper.get('topic_category', 'unknown')
        relevance_score = paper.get('relevance_score', 0)
        ai_summary = paper.get('ai_summary', paper.get('summary', ''))
        arxiv_url = paper.get('arxiv_url', '#')
        paper_id = paper.get('paper_id', '')
        matched_keywords = paper.get('matched_keywords', [])
        
        # 🆕 提取论文质量评估信息
        quality_score = paper.get('quality_score')
        quality_level = paper.get('quality_level')
        quality_reasoning = paper.get('quality_reasoning')
        
        # 格式化作者
        authors_str = ', '.join(authors[:3])
        if len(authors) > 3:
            authors_str += f' 等'
        
        # 格式化关键词
        keywords_str = ', '.join(matched_keywords[:5]) if matched_keywords else '无'
        if len(matched_keywords) > 5:
            keywords_str += f' 等'
        
        # 主题标签配置
        topic_labels = {
            'image_denoising': '🖼️ 图像去噪',
            'image_deraining': '🌧️ 图像去雨',
            'reinforcement_learning': '🤖 强化学习',
            'embodied_ai': '🦾 具身智能',
            'computer_vision': '👁️ 计算机视觉',
            'deep_learning': '🧠 深度学习'
        }
        topic_label = topic_labels.get(topic, f'📌 {topic}')
        
        # 🆕 生成质量评估徽章
        quality_badge_html = ""
        if quality_score is not None and quality_level:
            # 根据评分生成星级
            stars = "⭐" * min(quality_score, 10)
            
            # 根据评分确定样式
            if quality_score >= 9:
                badge_class = "quality-top"
                emoji = "🏆"
            elif quality_score >= 7:
                badge_class = "quality-excellent"
                emoji = "⭐"
            elif quality_score >= 5:
                badge_class = "quality-good"
                emoji = "✅"
            elif quality_score >= 3:
                badge_class = "quality-normal"
                emoji = "📝"
            else:
                badge_class = "quality-weak"
                emoji = "📄"
            
            quality_badge_html = f'<span class="quality-badge {badge_class}">{emoji} {quality_level} ({quality_score}/10)</span>'
        
        # 🆕 生成评估理由区块
        reasoning_html = ""
        if quality_reasoning:
            reasoning_html = f"""
                <div class="quality-reasoning">
                    <strong>💡 AI评估理由：</strong>{quality_reasoning}
                </div>
            """
        
        return f"""
            <div class="paper-card">
                <div>
                    <span class="paper-number">{index}</span>
                    <span class="paper-title">
                        <a href="{arxiv_url}" target="_blank">{title}</a>
                    </span>
                </div>
                
                <div class="paper-meta">
                    <span><strong>📅 发布：</strong>{published}</span>
                    <span><strong>📄 ID：</strong>{paper_id}</span>
                </div>
                
                <div class="paper-authors">
                    ✍️ 作者：{authors_str}
                </div>
                
                <div style="margin: 10px 0;">
                    <span class="paper-topic">{topic_label}</span>
                    <span class="paper-score">相关性: {relevance_score:.1%}</span>
                    {quality_badge_html}
                </div>
                
                <div class="paper-summary">
                    <strong>🤖 AI核心思想总结：</strong><br>
                    {ai_summary}
                </div>
                
                {reasoning_html}
                
                <div class="paper-keywords">
                    <strong>🏷️ 关键词：</strong>{keywords_str}
                </div>
                
                <a href="{arxiv_url}" target="_blank" class="paper-link">
                    📖 查看原文 &rarr;
                </a>
            </div>
"""

    @staticmethod
    def get_footer() -> str:
        """
        生成邮件底部
        
        Returns:
            HTML底部
        """
        return """
        </div>
        
        <div class="footer">
            <div class="divider"></div>
            <p>
                这是一份自动生成的Arxiv论文日报。<br>
                由 <strong>Arxiv Mailbot</strong> 驱动，使用DeepSeek AI生成论文总结与评估。<br>
                <a href="https://github.com/JiJiwjz/SamArM">项目源码</a> | 
                <a href="mailto:support@example.com">反馈建议</a>
            </p>
            <p style="margin-top: 10px; color: #ccc;">
                © 2025 Arxiv Mailbot. 自动化论文推荐系统
            </p>
        </div>
    </div>
</body>
</html>
"""

    @classmethod
    def generate_email_html(cls, papers: list, topic_stats: dict = None) -> str:
        """
        生成完整的邮件HTML
        
        Args:
            papers: 论文列表（已排序）
            topic_stats: 主题统计
        
        Returns:
            完整的HTML邮件内容
        """
        date_str = datetime.utcnow().strftime('%Y年%m月%d日')
        
        html = cls.get_header(date_str, len(papers), topic_stats)
        
        for i, paper in enumerate(papers, 1):
            html += cls.get_paper_card(i, paper)
        
        html += cls.get_footer()
        
        return html
