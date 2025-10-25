# Arxiv-Mailbox

一个自动化的 Arxiv 论文日报系统：从爬取 → 去重 → 分类筛选 → AI 总结（DeepSeek） → 邮件格式化与发送 → 定时调度，全流程打通。

- 灵活关键词/学科配置（支持 OR/AND/分类等模式）
- 智能主题分类与相关性打分（保留分数供后续使用）
- DeepSeek 异步并发总结，失败自动降级为摘要截断
- 精美 HTML 邮件模板 + 纯文本备选
- 每日定时推送，支持仅推送“新论文”
- 结果落盘（HTML 日报 + JSON 报告），可留档回溯

> 当前版本：v0.1.0

---

## 目录

- [环境要求](#环境要求)
- [安装与初始化](#安装与初始化)
- [配置说明](#配置说明)
  - [.env（敏感配置）](#env敏感配置)
  - [config.yaml（业务配置）](#configyaml业务配置)
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

```env
# ============ DeepSeek API ============
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxx
DEEPSEEK_API_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT=30

# ============ 邮件（推荐 QQ 邮箱） ============
SENDER_EMAIL=your@qq.com
SENDER_PASSWORD=your_smtp_authcode         # QQ 邮箱需“授权码”
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465                               # QQ 推荐 465 + SSL
SMTP_USE_SSL=true
SMTP_USE_TLS=false
SMTP_TIMEOUT=25
SMTP_MAX_RETRIES=1                          # 默认仅尝试 1 次，避免“报错但已投递”的重复发送
# 多收件人用 | 分隔
RECIPIENT_EMAILS=foo@bar.com|another@bar.com

# ============ 日志 ============
LOG_LEVEL=INFO
```

> QQ 邮箱需在「设置 → 账户 → POP3/SMTP 服务」开启，并使用授权码，而非登录密码。

### config.yaml（业务配置）

```yaml
arxiv:
  keywords:
    - "image denoising"
    - "image deraining"
    - "reinforcement learning"
    - "embodied AI"
  categories:
    - "cs.CV"
    - "cs.AI"
    - "cs.LG"
  max_results: 50
  sort_by: "submittedDate"  # 可选: submittedDate|relevance|lastUpdatedDate

email:
  subject_prefix: "【Arxiv论文日报】"

deepseek:
  # 可在此覆盖 .env 的默认（通常保持为空）
  # model: "deepseek-chat"
  # timeout: 30
```

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
  python main.py schedule --time 08:30 --tz Asia/Shanghai
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
- 多为时间窗口过窄。将 `--days-back` 从 1 调整为 3 或 7。  
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
├─ src/
│  ├─ crawler/           # arxiv 爬虫
│  ├─ filter/            # 去重 + 主题分类 + 相关性评分
│  ├─ extractor/         # DeepSeek 客户端 + 思想提取（异步批处理）
│  ├─ sender/            # 邮件模板 + 格式化 + 发送（默认仅尝试一次）
│  └─ pipeline/          # DailyJob 编排（整合全流程）
├─ data/                 # 去重缓存与本地数据
├─ out/                  # 产出HTML日报与JSON报告（已忽略）
├─ main.py               # CLI 入口（run-once/schedule）
├─ test_*.py             # 各阶段独立测试脚本
├─ config.yaml           # 业务配置
├─ .env                  # 敏感配置（不提交）
├─ .env.example          # 环境变量模板
├─ requirements.txt
└─ README.md
```

---

## 开发建议

- 搜索范围与策略可在 `ArxivCrawler` 中调整（OR/AND/keyword_only/category_only）。
- 邮件模板在 `src/sender/email_templates.py` 中可自定义样式与字段。
- DeepSeek 并发 `--batch-size` 取 2–5 更稳妥；`--top-n` 控制每日总结数量。
- 版本发布建议：
  ```bash
  git tag v0.1.0
  git push origin v0.1.0
  ```

---

## 许可证

本项目仅用于学习与研究目的。若需开源许可证（如 MIT/Apache-2.0），可在根目录添加 LICENSE 文件后在此处声明。
