# Sam_ArM

Sam_ArM (Arxiv-Mailbox) 是一个自动化的 Arxiv 论文日报系统，专注于 **Image Restoration（图像复原）** 方向（去噪、去模糊、去雨、去雾、超分辨率、补全、低光增强等）。每天从 Arxiv 上找出该领域的新文章，根据相关性进行排序，并基于 AI 解读（部分代码使用 Claude 辅助编写）。这个项目的流程可以总结为：
> 爬取 → 去重 → 分类筛选 → AI 总结（DeepSeek） → 邮件格式化与发送 → 定时调度，全流程打通

- 聚焦 Image Restoration 方向的关键词/分类配置与主题过滤
- 智能主题分类与相关性打分（保留分数供后续使用）
- DeepSeek（deepseek-v4-flash）异步并发总结与五维度质量评估，失败自动降级为摘要截断
- 摘要按「背景→现有方法→不足→动机→核心思路→主实验（含数据集）→总结」结构生成，纯文本无 Markdown 标记
- 自动抓取论文 Overview 配图（arXiv HTML 版首图）嵌入邮件
- 精美 HTML 邮件模板（Light Mode）+ 纯文本备选
- 0 篇兜底机制：时间窗口自动逐级放大（1→2→3→5→7 天），仍无新论文时降级回顾最近 7 天，避免空推送
- GitHub Actions 每日自动推送，支持仅推送"新论文"
- 结果落盘（HTML 日报 + JSON 报告），可留档回溯

> 当前版本：v0.2.0

---

## 目录

- [环境要求](#环境要求)
- [安装与初始化](#安装与初始化)
- [配置说明](#配置说明)
  - [.env（敏感配置）](#env敏感配置)
  - [config.yaml（业务配置）](#configyaml业务配置)
- [GitHub Actions 部署（推荐）](#github-actions-部署推荐)
- [快速开始](#快速开始)
- [命令行使用](#命令行使用)
- [模块化测试](#模块化测试)
- [缓存与去重](#缓存与去重)
- [产出与归档](#产出与归档)
- [常见问题与排错](#常见问题与排错)
- [项目结构](#项目结构)
- [开发建议](#开发建议)
- [许可证](#许可证)

---

## 环境要求

- Python 3.9+
- 可访问 arxiv.org 与 DeepSeek API 的网络
- 可用的邮箱 SMTP（推荐 QQ 邮箱：smtp.qq.com）

---

## 安装与初始化

```bash
# 克隆仓库并进入
git clone https://github.com/JiJiwjz/Arxiv-Mailbox.git
cd Arxiv-Mailbox

# 可选：创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 准备数据与输出目录
mkdir -p data out

# 初始化去重缓存（可选）
echo '{"records": {}, "updated_at": "", "total_count": 0}' > data/processed_papers.json
```

---

## 配置说明

### .env（敏感配置）

根据 [.env.example](./.env.example) 创建 `.env`，填写实际密钥。`.env` 已加入 `.gitignore`，请勿提交到 Git。
在终端输入以下内容：
```bash
cd Arxiv-Mailbox
vim .env
```

随后，将以下内容放到 `.env` 中即可，记得修改为**你**的信息：
```env
# ============ DeepSeek API ============
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxx
DEEPSEEK_API_URL=https://api.deepseek.com/v1 # 可以不用改
DEEPSEEK_MODEL=deepseek-v4-flash             # 可以不用改
DEEPSEEK_TIMEOUT=60

# ============ 邮件（以 QQ 邮箱为例） ============
SENDER_EMAIL=your@qq.com
SENDER_PASSWORD=your_smtp_authcode         # QQ 邮箱需“授权码”
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465                               # QQ 推荐 465 + SSL
SMTP_USE_SSL=true
SMTP_USE_TLS=false
SMTP_TIMEOUT=25
SMTP_MAX_RETRIES=1                          # 默认仅尝试 1 次，避免“报错但已投递”的重复发送
# 如果有多个收件人的邮箱，每两个邮箱之间用 | 分隔
RECIPIENT_EMAILS=foo@bar.com|another@bar.com

# ============ 日志 ============
LOG_LEVEL=INFO
```

> QQ 邮箱需在「设置 → 账户 → POP3/SMTP 服务」开启，并使用授权码，而非登录密码。

### config.yaml（业务配置）

```yaml
arxiv:
  keywords:                      # 仅 Image Restoration 方向，可按需增删
    - "image restoration"
    - "image denoising"
    - "image deblurring"
    - "image deraining"
    - "image dehazing"
    - "image super-resolution"
    - "image inpainting"
    - "low-light image enhancement"
  categories:
    - "cs.CV"
    - "eess.IV"
  max_results: 50
  sort_by: "submittedDate"  # 可选: submittedDate|relevance|lastUpdatedDate
  search_mode: "keyword_only"  # 仅关键词检索，避免分类结果挤占上限

email:
  subject_prefix: "【Image Restoration日报】"

deepseek:
  # 可在此覆盖 .env 的默认（通常保持为空）
  # model: "deepseek-v4-flash"
  # timeout: 60
```

> 说明：论文筛选由 `src/filter/paper_filter.py` 中 Image Restoration 专属主题词库把关，
> 未命中任何复原关键词的论文会被直接过滤，邮件中只会出现该方向的内容。

---

## GitHub Actions 部署（推荐）

仓库内置工作流 [.github/workflows/daily.yml](./.github/workflows/daily.yml)，**每天北京时间 09:00**（UTC 01:00）自动运行完整流程并发送邮件，也可在 Actions 页面手动触发（Run workflow）。

### 配置步骤

在仓库页面进入 **Settings → Secrets and variables → Actions → New repository secret**，依次添加：

| Secret 名称 | 说明 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（从 platform.deepseek.com 获取） |
| `SENDER_EMAIL` | 发件邮箱地址（如 QQ 邮箱） |
| `SENDER_PASSWORD` | 邮箱 SMTP 授权码（QQ 邮箱需在设置中开启 SMTP 并获取授权码） |
| `SMTP_SERVER` | SMTP 服务器（如 `smtp.qq.com`） |
| `SMTP_PORT` | SMTP 端口（SSL 用 `465`，STARTTLS 用 `587`） |
| `RECIPIENT_EMAILS` | 收件人邮箱，多个用 `\|` 分隔 |

配置完成后，到 **Actions → Daily Image Restoration Report → Run workflow** 手动跑一次验证，成功后每日自动执行。

### 工作流细节

- 去重缓存 `data/processed_papers.json` 通过 `actions/cache` 在多次运行间持久化，保证"仅推送新论文"在云端同样生效；
- 每次运行生成的 HTML 日报与 JSON 报告会作为 Artifact 保留 14 天，可在运行记录页下载；
- GitHub 定时任务在高峰期可能延迟几分钟，属正常现象；
- 如需调整推送时间，修改 `daily.yml` 中的 cron 表达式（注意使用 UTC 时间）。

---

## 快速开始

一次性跑完整流程（默认回溯 3 天、Top 10、并发 3、只推新论文、发送邮件）：

```bash
python main.py run-once
```

常用参数：
- `--days-back 7` 回溯 7 天
- `--top-n 12` 发送前取前 12 篇（用于 AI 总结与邮件）
- `--batch-size 5` DeepSeek 并发批大小（2–5 较稳妥）
- `--include-all` 包含历史已处理论文（默认仅推送新论文）
- `--no-email` 不发送邮件，仅生成 HTML
- `--html-out out/custom_daily.html` 指定输出路径

示例：
```bash
python main.py run-once --days-back 7 --top-n 12 --no-email --html-out out/daily_test.html
```

---

## 命令行使用

- 立即运行一次日报
  ```bash
  python main.py run-once \
    --days-back 3 \
    --top-n 10 \
    --batch-size 3 \
    # --include-all    # 如需包含历史已处理论文
    # --no-email       # 如不发送邮件
    # --html-out out/daily_YYYYMMDD.html
  ```

- 每日定时运行（默认 Asia/Shanghai）
  ```bash
  # 需要：pip install apscheduler pytz
  python main.py schedule --time 09:00 --tz Asia/Shanghai
  ```

---

## 模块化测试

分步骤验证各模块：

1) 爬虫
```bash
python test_crawler.py
python test_crawler_verbose.py   # 查看时间过滤与查询语句
```

2) 去重 + 分类筛选
```bash
python test_filter.py
```

3) DeepSeek 总结（默认抽取前若干篇，测试脚本示例为 10 篇）
```bash
python test_extractor.py
```

4) 邮件格式化与发送（流程含交互式确认）
```bash
python test_sender.py
```

---

## 缓存与去重

- 去重缓存：`data/processed_papers.json`（基于标题 + 前若干作者指纹）
- 一键清空缓存：
  - 命令行：
    ```bash
    rm -f data/processed_papers.json
    echo '{"records": {}, "updated_at": "", "total_count": 0}' > data/processed_papers.json
    ```
  - 代码：
    ```python
    from src.filter import Deduplicator
    Deduplicator().clear_cache()
    ```

- 使用 `--include-all` 可忽略缓存，推送历史论文（适合回测/回看）。

---

## 产出与归档

- HTML 日报：`out/daily_YYYYMMDD.html`
- 运行报告（统计 JSON）：`out/report_YYYYMMDD.json`
- 默认 `out/` 目录已加入 `.gitignore`，不建议纳入版本管理。

---

## 常见问题与排错

1) 收到邮件但控制台显示 SMTP 错误  
- 某些服务商在 DATA 后断开连接（如 QQ 邮箱），实则已投递。  
- 推荐 `SMTP_SSL + 465`，并将重试次数设置为 1（本项目默认即为 1）。  
- 相关参数：`SMTP_PORT=465, SMTP_USE_SSL=true, SMTP_USE_TLS=false, SMTP_MAX_RETRIES=1`。

2) 邮件显示“0 篇内容”或主题/相关性为 unknown/0%  
- 请使用 `main.py run-once` 或 `test_sender.py`（已合并筛选元数据与 AI 总结，确保 `topic_category`/`relevance_score` 不丢失）。  
- 若自定义脚本，请在邮件格式化前将筛选阶段的元数据合并回 AI 总结结果（按 `paper_id`）。

3) 爬虫返回 0 条  
- 多为时间窗口过窄。流水线已内置兜底：窗口会自动从 `--days-back` 逐级放大到 2/3/5/7 天；仍为 0 时降级回顾最近 7 天论文（含已推送过的），不会再发出 0 篇的空邮件。  
- 也可用 `test_crawler_verbose.py` 查看查询语句与时间边界。

4) arxiv 速率限制  
- 已内置节流（如 `time.sleep(0.5)`）。如需更快可自行调整，但需注意 API 限制。

5) API Key 安全  
- `.env` 已加入 `.gitignore`。请勿将真实密钥提交到 Git。  
- 可提供 `.env.example` 用作模板。

---

## 项目结构

```
Arxiv-Mailbox/
├─ .github/workflows/    # GitHub Actions 每日定时工作流
├─ src/
│  ├─ crawler/           # arxiv 爬虫
│  ├─ filter/            # 去重 + 主题分类 + 相关性评分（Image Restoration 词库）
│  ├─ extractor/         # DeepSeek 客户端 + 思想提取（异步批处理）
│  ├─ sender/            # 邮件模板 + 格式化 + 发送（默认仅尝试一次）
│  └─ pipeline/          # DailyJob 编排（整合全流程）
├─ data/                 # 去重缓存与本地数据
├─ out/                  # 产出HTML日报与JSON报告（已忽略）
├─ main.py               # CLI 入口（run-once/schedule）
├─ preview_email.py      # 邮件模板本地预览（模拟数据 + 浏览器打开）
├─ test_*.py             # 各阶段独立测试脚本
├─ config.yaml           # 业务配置
├─ .env                  # 敏感配置（不提交）
├─ .env.example          # 环境变量模板
├─ requirements.txt
└─ README.md
```

