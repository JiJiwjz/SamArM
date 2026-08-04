"""
邮件模板
定义HTML邮件的样式和结构（Image Restoration 专题日报 · Light Mode）
"""

from datetime import datetime


class EmailTemplate:
    """邮件模板类"""

    # 主题标签配置（Image Restoration 子方向）
    TOPIC_LABELS = {
        'image_restoration': '图像复原',
        'image_denoising': '图像去噪',
        'image_deblurring': '图像去模糊',
        'image_deraining': '图像去雨',
        'image_dehazing': '图像去雾',
        'super_resolution': '超分辨率',
        'image_inpainting': '图像补全',
        'low_light_enhancement': '低光增强',
    }

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
        topic_chips = ""
        if topic_stats:
            chips = []
            for topic, count in sorted(topic_stats.items(), key=lambda x: x[1], reverse=True):
                label = EmailTemplate.TOPIC_LABELS.get(topic, topic)
                chips.append(f"<span class='chip'>{label}&nbsp;<b>{count}</b></span>")
            topic_chips = "".join(chips)

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Restoration 论文日报 · {date_str}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Noto+Sans+SC:wght@400;500;700;900&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Manrope', -apple-system, BlinkMacSystemFont, 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Segoe UI', Roboto, Arial, sans-serif;
            line-height: 1.7;
            color: #3f3f46;
            background-color: #f4f4f2;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 720px;
            margin: 0 auto;
            background-color: #ffffff;
        }}

        /* ===== 刊头 ===== */
        .masthead {{
            padding: 48px 44px 36px 44px;
            background: radial-gradient(ellipse 90% 70% at 15% 0%, rgba(249, 115, 22, 0.10) 0%, rgba(249, 115, 22, 0) 60%), #ffffff;
            border-bottom: 1px solid #ececee;
        }}

        .kicker {{
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 11px;
            letter-spacing: 4px;
            color: #d97706;
            font-weight: 700;
            margin-bottom: 20px;
        }}

        .kicker .dot {{
            display: inline-block;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: #f97316;
            margin-right: 10px;
            vertical-align: 1px;
        }}

        .masthead h1 {{
            font-size: 42px;
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.5px;
            color: #18181b;
        }}

        .masthead h1 .accent {{
            color: #f97316;
        }}

        .masthead .date-line {{
            margin-top: 14px;
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 12px;
            color: #a1a1aa;
            letter-spacing: 1px;
        }}

        .stat-row {{
            margin-top: 30px;
        }}

        .stat-big {{
            display: inline-block;
            vertical-align: middle;
        }}

        .stat-big .num {{
            font-size: 40px;
            font-weight: 800;
            color: #f97316;
            line-height: 1;
        }}

        .stat-big .unit {{
            font-size: 12px;
            color: #a1a1aa;
            margin-left: 8px;
            letter-spacing: 1px;
        }}

        .chips {{
            margin-top: 16px;
        }}

        .chip {{
            display: inline-block;
            font-size: 12px;
            color: #78716c;
            background-color: #fafaf9;
            border: 1px solid #e7e5e4;
            border-radius: 999px;
            padding: 4px 12px;
            margin: 4px 6px 0 0;
        }}

        .chip b {{
            color: #d97706;
            font-weight: 700;
        }}

        /* ===== 正文 ===== */
        .content {{
            padding: 12px 44px 8px 44px;
        }}

        .card {{
            background-color: #ffffff;
            border: 1px solid #ececee;
            border-radius: 16px;
            padding: 28px 26px 24px 26px;
            margin: 22px 0;
            box-shadow: 0 2px 10px rgba(24, 24, 27, 0.05);
        }}

        .card-head {{
            margin-bottom: 14px;
        }}

        .idx {{
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 13px;
            font-weight: 700;
            color: #f97316;
            letter-spacing: 1px;
        }}

        .topic-tag {{
            font-size: 11px;
            letter-spacing: 2px;
            color: #78716c;
            border: 1px solid #e4e4e7;
            border-radius: 999px;
            padding: 3px 11px;
            margin-left: 10px;
        }}

        .badge {{
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 3px 11px;
            border-radius: 999px;
            margin-left: 10px;
            border: 1px solid transparent;
        }}

        .badge-top {{
            color: #b45309;
            background-color: #fef3c7;
            border-color: #fcd34d;
        }}

        .badge-excellent {{
            color: #047857;
            background-color: #d1fae5;
            border-color: #6ee7b7;
        }}

        .badge-good {{
            color: #1d4ed8;
            background-color: #dbeafe;
            border-color: #93c5fd;
        }}

        .badge-normal {{
            color: #57534e;
            background-color: #f5f5f4;
            border-color: #e7e5e4;
        }}

        .badge-weak {{
            color: #a1a1aa;
            background-color: #fafaf9;
            border-color: #e4e4e7;
        }}

        .title {{
            font-size: 19px;
            font-weight: 700;
            line-height: 1.5;
            margin-bottom: 10px;
        }}

        .title a {{
            color: #18181b;
            text-decoration: none;
        }}

        .title a:hover {{
            color: #ea580c;
        }}

        .meta {{
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 11.5px;
            color: #a1a1aa;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
        }}

        .authors {{
            font-size: 12.5px;
            color: #78716c;
            margin-bottom: 4px;
        }}

        /* ===== 区块标签 ===== */
        .label {{
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 3px;
            color: #27272a;
            border-left: 3px solid #f97316;
            padding-left: 10px;
            margin: 22px 0 12px 0;
        }}

        .summary {{
            font-size: 13.5px;
            line-height: 1.9;
            color: #3f3f46;
            text-align: justify;
        }}

        /* ===== Overview 配图 ===== */
        .overview {{
            margin: 14px 0 4px 0;
        }}

        .overview img {{
            display: block;
            width: 100%;
            border-radius: 10px;
            border: 1px solid #ececee;
        }}

        /* ===== 五维度评分 ===== */
        .dim-row {{
            margin-bottom: 9px;
            font-size: 0;
        }}

        .dim-name {{
            display: inline-block;
            width: 88px;
            font-size: 12px;
            color: #78716c;
            vertical-align: middle;
        }}

        .dim-track {{
            display: inline-block;
            width: 58%;
            height: 5px;
            background-color: #eeeeef;
            border-radius: 999px;
            vertical-align: middle;
            overflow: hidden;
        }}

        .dim-fill {{
            display: block;
            height: 5px;
            border-radius: 999px;
            background: linear-gradient(90deg, #f59e0b, #ea580c);
        }}

        .dim-score {{
            display: inline-block;
            width: 46px;
            text-align: right;
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 12.5px;
            font-weight: 700;
            color: #d97706;
            vertical-align: middle;
        }}

        /* ===== 评语 / 优缺点 ===== */
        blockquote {{
            margin: 4px 0 0 0;
            padding: 2px 0 2px 16px;
            border-left: 2px solid #f97316;
            font-size: 12.5px;
            line-height: 1.9;
            color: #78716c;
            font-style: italic;
        }}

        .pros, .cons {{
            padding: 12px 16px;
            font-size: 12.5px;
            margin-top: 10px;
            border-radius: 10px;
        }}

        .pros {{
            background-color: #f0fdf4;
            border: 1px solid #bbf7d0;
        }}

        .cons {{
            background-color: #fff1f2;
            border: 1px solid #fecdd3;
        }}

        .pros strong, .cons strong {{
            display: block;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
            margin-bottom: 5px;
        }}

        .pros strong {{ color: #15803d; }}
        .cons strong {{ color: #be123c; }}

        .pros ul, .cons ul {{
            padding-left: 16px;
            color: #3f3f46;
            line-height: 1.8;
        }}

        /* ===== 关键词与按钮 ===== */
        .keywords {{
            margin-top: 18px;
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 11px;
            color: #b6b2ab;
            letter-spacing: 0.5px;
        }}

        .read-btn {{
            display: inline-block;
            margin-top: 16px;
            padding: 10px 24px;
            background: linear-gradient(135deg, #fbbf24, #f97316);
            color: #18181b;
            text-decoration: none;
            font-size: 12.5px;
            font-weight: 700;
            letter-spacing: 1px;
            border-radius: 999px;
        }}

        /* ===== 页脚 ===== */
        .colophon {{
            padding: 30px 44px 40px 44px;
            text-align: center;
            border-top: 1px solid #ececee;
        }}

        .colophon .glow {{
            width: 48px;
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, #f59e0b, #ea580c);
            margin: 0 auto 18px auto;
        }}

        .colophon p {{
            font-size: 12px;
            color: #a1a1aa;
            line-height: 2;
        }}

        .colophon .brand {{
            font-family: 'JetBrains Mono', 'SF Mono', Consolas, 'Courier New', monospace;
            font-size: 12px;
            letter-spacing: 2px;
            color: #78716c;
        }}

        .colophon a {{
            color: #d97706;
            text-decoration: none;
        }}

        @media only screen and (max-width: 600px) {{
            .masthead {{
                padding: 34px 22px 28px 22px;
            }}

            .masthead h1 {{
                font-size: 30px;
            }}

            .content {{
                padding: 8px 16px 4px 16px;
            }}

            .card {{
                padding: 20px 16px 18px 16px;
                border-radius: 14px;
            }}

            .title {{
                font-size: 16.5px;
            }}

            .dim-name {{
                width: 78px;
                font-size: 11px;
            }}

            .dim-track {{
                width: 48%;
            }}

            .colophon {{
                padding: 24px 22px 32px 22px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="masthead">
            <div class="kicker"><span class="dot"></span>IMAGE RESTORATION DAILY</div>
            <h1>Image Restoration<br><span class="accent">论文日报</span></h1>
            <div class="date-line">{date_str} · POWERED BY DEEPSEEK AI</div>
            <div class="stat-row">
                <span class="stat-big"><span class="num">{total_papers:02d}</span><span class="unit">篇今日精选</span></span>
            </div>
            <div class="chips">{topic_chips}</div>
        </div>

        <div class="content">
"""

    @staticmethod
    def _dimension_row(label: str, score: float) -> str:
        """生成单个维度的评分进度条"""
        pct = max(0, min(100, score * 10))
        return f"""
                        <div class="dim-row">
                            <span class="dim-name">{label}</span>
                            <span class="dim-track"><span class="dim-fill" style="width: {pct:.0f}%;"></span></span>
                            <span class="dim-score">{score:.1f}</span>
                        </div>"""

    @staticmethod
    def get_paper_card(index: int, paper: dict) -> str:
        """
        生成单篇论文的卡片HTML

        Args:
            index: 论文序号
            paper: 论文信息字典（包含AI总结和质量评估）

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

        # 提取五维度评分
        quality_score = paper.get('quality_score')
        quality_level = paper.get('quality_level')
        quality_reasoning = paper.get('quality_reasoning')
        innovation = paper.get('innovation_score')
        practicality = paper.get('practicality_score')
        technical_depth = paper.get('technical_depth_score')
        experimental_rigor = paper.get('experimental_rigor_score')
        impact_potential = paper.get('impact_potential_score')
        strengths = paper.get('strengths', [])
        weaknesses = paper.get('weaknesses', [])

        # 格式化作者
        authors_str = ', '.join(authors[:3])
        if len(authors) > 3:
            authors_str += ' et al.'

        # 格式化关键词
        keywords_str = ' · '.join(matched_keywords[:5]) if matched_keywords else '—'
        if len(matched_keywords) > 5:
            keywords_str += ' …'

        # 主题标签
        topic_label = EmailTemplate.TOPIC_LABELS.get(topic, topic)

        # Overview 配图（arXiv HTML版首图，可能不存在）
        overview_html = ""
        overview_image = paper.get('overview_image')
        if overview_image:
            overview_html = f"""
                <div class="overview">
                    <img src="{overview_image}" alt="论文方法概览图">
                </div>
            """

        # 生成质量评估徽章
        badge_html = ""
        if quality_score is not None and quality_level:
            if quality_score >= 9:
                badge_class = "badge-top"
                mark = "★★★"
            elif quality_score >= 7:
                badge_class = "badge-excellent"
                mark = "★★"
            elif quality_score >= 5:
                badge_class = "badge-good"
                mark = "★"
            elif quality_score >= 3:
                badge_class = "badge-normal"
                mark = "·"
            else:
                badge_class = "badge-weak"
                mark = "·"

            badge_html = f'<span class="badge {badge_class}">{mark} {quality_level} {quality_score:.1f}</span>'

        # 生成五维度评分进度条
        dimensions_html = ""
        if all(v is not None for v in [innovation, practicality, technical_depth, experimental_rigor, impact_potential]):
            rows = (
                EmailTemplate._dimension_row("创新性", innovation)
                + EmailTemplate._dimension_row("实用性", practicality)
                + EmailTemplate._dimension_row("技术深度", technical_depth)
                + EmailTemplate._dimension_row("实验完整性", experimental_rigor)
                + EmailTemplate._dimension_row("影响力潜力", impact_potential)
            )
            dimensions_html = f"""
                <div class="label">评 分</div>
                {rows}
            """

        # 生成评估理由区块
        reasoning_html = ""
        if quality_reasoning:
            reasoning_html = f"""
                <div class="label">评 语</div>
                <blockquote>{quality_reasoning}</blockquote>
            """

        # 优点和不足
        pros_cons_html = ""
        if strengths or weaknesses:
            pros_html = ""
            if strengths:
                pros_items = "".join([f"<li>{s}</li>" for s in strengths[:3]])
                pros_html = f"""
                    <div class="pros">
                        <strong>+ 优点</strong>
                        <ul>{pros_items}</ul>
                    </div>
                """

            cons_html = ""
            if weaknesses:
                cons_items = "".join([f"<li>{w}</li>" for w in weaknesses[:3]])
                cons_html = f"""
                    <div class="cons">
                        <strong>− 不足</strong>
                        <ul>{cons_items}</ul>
                    </div>
                """

            pros_cons_html = pros_html + cons_html

        return f"""
            <div class="card">
                <div class="card-head">
                    <span class="idx">{index:02d}</span>
                    <span class="topic-tag">{topic_label}</span>
                    {badge_html}
                </div>

                <div class="title">
                    <a href="{arxiv_url}" target="_blank">{title}</a>
                </div>

                <div class="meta">{published} &nbsp;·&nbsp; arXiv:{paper_id} &nbsp;·&nbsp; REL {relevance_score:.0%}</div>
                <div class="authors">{authors_str}</div>

                {overview_html}

                <div class="label">摘 要</div>
                <div class="summary">{ai_summary}</div>

                {dimensions_html}
                {reasoning_html}
                {pros_cons_html}

                <div class="keywords">{keywords_str}</div>

                <a href="{arxiv_url}" target="_blank" class="read-btn">阅读原文 &rarr;</a>
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

        <div class="colophon">
            <div class="glow"></div>
            <p class="brand">SamArM · IMAGE RESTORATION DAILY</p>
            <p>
                本刊由 SamArM 自动生成 · DeepSeek AI 撰写摘要与评估<br>
                <a href="https://github.com/JiJiwjz/SamArM">github.com/JiJiwjz/SamArM</a>
            </p>
            <p>© 2025 SamArM</p>
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
