# SamArM：机器人学习论文日报

每天检索 arXiv 机器人学习论文，筛选与去重，生成中文解读和基于摘要的五维初评，通过邮件发送，并保存 HTML / JSON 报告。

## 收录范围

所有主题都必须与机器人相关：

- 具身智能：机械臂、灵巧手、抓取、双臂协作、接触操作等。
- 模仿学习：行为克隆、从示范学习、Diffusion Policy 等。
- VLA：Vision-Language-Action 模型与机器人策略。
- ICL：In-Context Learning / 上下文适应在机器人上的应用。
- RL：机器人强化学习、离线 RL、策略优化等。

暂不收录人形机器人；纯导航、步态或飞行任务不在当前范围。通用语言模型 ICL、纯文本 RL、图像复原等不收录。筛选基于标题和摘要中的关键词，包含人形关键词的论文会被严格排除，即使也讨论操作任务。

检索关键词、分类和上限在 `config.yaml` 的 `arxiv` 中配置；主题词库和排除规则在 `src/filter/research_topics.py`。检索端和本地筛选端均开启 `robotics_only`，不要只修改一处。

## GitHub Actions 部署

工作流：`.github/workflows/daily.yml`，名称 **Daily Robotics Learning Report**。

在仓库 Settings → Secrets and variables → Actions 添加以下 Repository Secrets：

| Secret | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `SENDER_EMAIL` | 发件邮箱 |
| `SENDER_PASSWORD` | SMTP 授权码 |
| `SMTP_SERVER` | 例如 `smtp.qq.com` |
| `SMTP_PORT` | QQ 邮箱建议 `465`，自动使用 SSL |
| `RECIPIENT_EMAILS` | 多个收件人以 `|` 分隔 |

默认模型为 `deepseek-flash`。使用 JSON 输出约束、关闭思考模式以控制耗时；评分要求所有数值字段有效，空响应、截断、无效 JSON、临时 HTTP 错误会有限重试。认证错误直接记录，不反复请求。

### 时间与补跑

| 北京时间 | 行为 |
| --- | --- |
| 08:43 | 提前检索并生成日报，准备好后等待到 09:00 才发送 |
| 10:23 | 补跑：当天投递完成则跳过；部分失败则复用同一份日报，只发送未成功的收件人 |
| 12:23 | 再次补跑，采用同样的防重复规则 |

GitHub Actions 的定时启动可能延迟或被丢弃，因此本方案以 09:00 为发送目标，无法保证准点。若任务在 09:00 后才启动，生成完成后立即发送。工作流设置并发锁，避免手动和定时任务同时投递。

公开仓库连续 60 天没有活动时，GitHub 会自动禁用定时工作流。附带的 `keep-schedule-active` 任务检查最后提交时间；超过 30 天才创建一个空提交以保持活动。仅该任务具有 `contents: write` 权限，日报任务保持只读。分支保护或仓库策略禁止机器人提交时，该任务会明确失败，应检查 Actions 日志并调整策略。

如果现有工作流已显示 `disabled_inactivity`，在 Actions 页面启用工作流，或通过 GitHub API 重新启用。仅查看或下载运行记录不能恢复定时任务。

### 缓存与产物

- `data/processed_papers.json`：已成功投递论文的去重记录。
- `data/daily_delivery.json`：当天日报及成功收件人的 SHA-256 标识，用于补跑；不保存 SMTP 密码或 API 密钥。
- 使用独立的 `robotics-delivery-v1-` 缓存前缀，恢复机器人日报的状态。
- 即使某些收件人发送失败，也保存状态，下一次只重试未成功的收件人。
- `out/` 的 HTML 与 JSON 报告作为 Artifact 保存 14 天，失败时也尝试上传。

防重复依赖状态缓存。缓存清理、驱逐或 SMTP 在 DATA 阶段出现无法确认的断连时，仍存在再次投递的可能，不能把 SMTP 当作严格的恰好一次消息系统。

## 本地运行

建议 Python 3.11：

```bash
git clone https://github.com/JiJiwjz/SamArM.git
cd SamArM
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

复制 `.env.example` 为 `.env`，填写真实配置。不要提交 `.env`。环境变量优先于 `config.yaml`；若旧环境变量仍指定图像复原关键词，需要同步更新或移除这些覆盖值。

```bash
# 立即生成并投递；当天仅投递一次
python main.py run-once --days-back 1 --top-n 10 --once-per-day

# 只生成预览，不发送、不消耗去重记录
python main.py run-once --days-back 3 --top-n 5 --no-email --html-out out/preview.html

# 提前启动，最早在北京时间 09:00 发送
python main.py run-once --once-per-day --send-at 09:00

# 常驻调度：进程和机器须保持运行，09:00 开始生成日报
python main.py schedule --time 09:00 --tz Asia/Shanghai
```

`--days-back`、`--top-n`、`--batch-size` 必须为正数。`--include-all` 可用于显式回看历史；正常自动任务只处理新论文。

## 筛选、解读与评分

每篇论文在作者下方显示完整作者单位列表，并附论文 HTML / PDF 首页的来源链接。优先读取 HTML 中明确标注的机构；缺少结构化单位时读取 PDF 首页，通过带原文证据的 JSON 提取，机构名和证据均必须能在来源文本中逐字核对，不从作者姓名或邮箱猜测。未获取时明确显示“未获取”。成功结果按论文版本缓存于 `data/author_affiliations.json`；单位抓取失败不会阻断解读、评分或投递。`affiliations.timeout` 与 `max_pdf_mb` 控制 PDF 下载耗时和大小上限。

一次检索最近至少 7 天，再在本地逐级尝试 1 / 2 / 3 / 5 / 7 天窗口；不会对同一组论文重复调用 arXiv。日期范围在查询端应用，避免旧论文挤占结果上限。默认最多检索 300 篇。

- 只有真正投递完成的精选论文才写入去重记录；预览、筛掉的论文和未进入 Top N 的论文保留后续处理机会。
- 所有窗口都没有新论文时，发送明确的“暂无新论文”状态邮件；不自动重复历史论文。
- arXiv 网络错误使任务失败并允许补跑，不把网络故障伪装为“暂无新论文”。
- 每篇生成一次中文解读、一次五维初评，避免重复评分调用。
- 评分仅代表基于摘要的阅读优先级；未披露的实验与数据不能视为已验证。
- 请求重试后仍未获得有效评分，显示“待评估”并保留论文和摘要；不再用关键词相关性编造质量分数。
- 缺失评分不会导致排序崩溃；排序综合初评分和相关性，HTML / 纯文本保持一致。
- SMTP 配置缺失或有收件人投递失败时，任务明确失败，报告保存原因。

## 验证

回归测试使用模拟接口和临时目录，不调用真实 API、不发送邮件：

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

覆盖主题边界、JSON / 分数校验、重试、无评分降级、去重时机、Top N、空日报、部分投递恢复与当天防重复。根目录的旧 `test_*.py` 为手动集成脚本，可能调用 API 或发送邮件，不属于上述离线测试集。

## 目录

```text
.github/workflows/daily.yml  定时运行、补跑、缓存和活动维护
src/crawler/                arXiv 检索与配图
src/filter/                 机器人主题筛选与去重
src/extractor/              中文解读、共享 API 重试
src/evaluator/              五维初评与字段校验
src/sender/                 邮件格式化和 SMTP 投递
src/pipeline/               日报编排和当天投递状态
src/config/                 YAML 与环境变量配置
src/notifier/               可选钉钉通知（Actions 默认关闭）
tests/                      离线回归测试
data/                       去重和投递缓存（不提交）
out/                        HTML / JSON 产物（不提交）
```
