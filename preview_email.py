#!/usr/bin/env python3
"""
本地预览脚本：用模拟数据渲染新版邮件HTML并在浏览器中打开
运行: python preview_email.py
"""

import os
import sys
import types
import webbrowser

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

# 绕过 src/__init__.py（避免导入 arxiv/openai 等重依赖），直接加载 sender 子模块
_pkg_src = types.ModuleType('src')
_pkg_src.__path__ = [os.path.join(ROOT, 'src')]
_pkg_sender = types.ModuleType('src.sender')
_pkg_sender.__path__ = [os.path.join(ROOT, 'src', 'sender')]
sys.modules.setdefault('src', _pkg_src)
sys.modules.setdefault('src.sender', _pkg_sender)

from src.sender.email_formatter import EmailFormatter

# 模拟两篇 Image Restoration 论文数据（字段与流水线输出一致）
MOCK_PAPERS = [
    {
        'paper_id': '2508.01234v1',
        'title': 'RestorFormerV2: All-in-One Image Restoration via Frequency-Aware Prompt Learning',
        'authors': ['Jian Zhang', 'Wei Li', 'Yuki Tanaka', 'Michael Chen'],
        'published': '2026-08-01T00:00:00',
        'topic_category': 'image_restoration',
        'relevance_score': 0.85,
        'matched_keywords': ['image restoration', 'all-in-one restoration', 'degradation model', 'denoising', 'deraining'],
        'arxiv_url': 'https://arxiv.org/abs/2508.01234',
        'ai_summary': '本文提出RestorFormerV2，一种面向全场景图像复原的Transformer框架。核心创新是频率感知提示学习机制：在网络各层注入可学习的频率先验提示，使单一模型无需针对特定退化类型微调即可同时处理去噪、去雨、去模糊、去雾等五种退化任务。方法在12个公开基准上取得SOTA，平均PSNR提升0.8dB，且参数量较上一代减少30%。实验表明频率提示对高频细节恢复起关键作用。',
        'quality_score': 8.7,
        'quality_level': '优秀',
        'quality_reasoning': '方法创新性强，将频率先验与提示学习结合用于全能型复原任务；实验覆盖全面，在多个退化基准上均验证有效；开源代码与预训练模型，实用性高。',
        'innovation_score': 9.0,
        'practicality_score': 8.5,
        'technical_depth_score': 8.8,
        'experimental_rigor_score': 8.6,
        'impact_potential_score': 8.5,
        'strengths': ['单一模型支持五种退化任务，部署成本低', '频率感知提示设计新颖，消融实验充分', '在12个基准上达到SOTA'],
        'weaknesses': ['对极端复合退化的泛化能力未充分验证', '推理延迟略高于专用小模型'],
    },
    {
        'paper_id': '2508.05678v1',
        'title': 'DiffRain: Controllable Rain Streak Removal with Latent Diffusion Priors',
        'authors': ['Anna Wang', 'Rui Liu', 'Carlos Garcia'],
        'published': '2026-07-31T00:00:00',
        'topic_category': 'image_deraining',
        'relevance_score': 0.72,
        'matched_keywords': ['deraining', 'rain removal', 'rain streak'],
        'arxiv_url': 'https://arxiv.org/abs/2508.05678',
        'ai_summary': '本文提出DiffRain，将潜在扩散模型的生成先验引入图像去雨任务。通过在潜空间建模雨条纹与干净背景的联合分布，实现可控强度的去雨效果。方法在Rain200H/L等数据集上去雨质量显著提升，真实雨天场景的视觉观感优于现有确定性方法。',
        'quality_score': 7.4,
        'quality_level': '良好',
        'quality_reasoning': '扩散先验用于去雨的思路较新颖，真实场景效果好；但推理需要多步采样，速度较慢，限制了实时应用。',
        'innovation_score': 8.0,
        'practicality_score': 6.5,
        'technical_depth_score': 7.5,
        'experimental_rigor_score': 7.2,
        'impact_potential_score': 7.0,
        'strengths': ['生成先验带来更自然的纹理恢复', '支持去雨强度可控调节'],
        'weaknesses': ['多步采样导致推理速度慢', '在极端暴雨场景下仍会残留雨痕'],
    },
    {
        'paper_id': '2508.09999v1',
        'title': 'LightSR: Lightweight Single Image Super-Resolution with Recursive State Space Blocks',
        'authors': ['Tom Brown', 'Lin Xiao'],
        'published': '2026-07-30T00:00:00',
        'topic_category': 'super_resolution',
        'relevance_score': 0.58,
        'matched_keywords': ['super-resolution', 'single image super-resolution', 'SISR'],
        'arxiv_url': 'https://arxiv.org/abs/2508.09999',
        'ai_summary': '本文提出LightSR，一种基于递归状态空间模块的轻量级超分辨率网络。通过状态空间模型的线性复杂度特性与参数递归共享，在保持重建质量的同时将参数量压缩至300K以下，适合移动端部署。',
        'quality_score': 6.2,
        'quality_level': '一般',
        'quality_reasoning': '轻量设计有实用价值，但创新点相对常规，实验对比的轻量基线不够全面。',
        'innovation_score': 6.5,
        'practicality_score': 7.5,
        'technical_depth_score': 6.0,
        'experimental_rigor_score': 5.5,
        'impact_potential_score': 5.8,
        'strengths': ['参数量小于300K，可移动端部署'],
        'weaknesses': ['缺少与最新Mamba类SR方法的对比', '高倍率(x4)重建细节偏软'],
    },
]


def main():
    formatter = EmailFormatter()
    html, stats = formatter.format_papers_to_html(MOCK_PAPERS)

    out_path = os.path.join(os.getcwd(), 'out', 'preview_email.html')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"预览文件已生成: {out_path}")
    print(f"统计: {stats}")

    # 在默认浏览器中打开
    webbrowser.open(f'file:///{out_path.replace(os.sep, "/")}')


if __name__ == '__main__':
    main()
