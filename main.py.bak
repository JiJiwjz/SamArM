#!/usr/bin/env python3
"""
Arxiv-Mailbox 主入口
支持：
- run-once：立即跑一次日报
- schedule：每天定时跑（APScheduler）
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from functools import partial

# 让本地包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import DailyJob

# 简单日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def cmd_run_once(args):
    job = DailyJob()
    stats = job.run(
        days_back=args.days_back,
        top_n=args.top_n,
        summary_batch_size=args.batch_size,
        only_new=not args.include_all,
        send_email=not args.no_email,
        html_out=args.html_out
    )
    print("\n✅ 运行完成：")
    for k, v in stats.items():
        if k not in ("email_stats", "send_result"):
            print(f"- {k}: {v}")
    if "send_result" in stats:
        print(f"- send_result: {stats['send_result']}")
    if "email_stats" in stats:
        print(f"- email_stats: {stats['email_stats']}")


def cmd_schedule(args):
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        import pytz
    except Exception:
        logger.error("需要安装 APScheduler 和 pytz: pip install apscheduler pytz")
        sys.exit(1)

    tz = pytz.timezone(args.tz)
    hh, mm = args.time.split(":")
    hh, mm = int(hh), int(mm)

    job = DailyJob()
    run_partial = partial(
        job.run,
        days_back=args.days_back,
        top_n=args.top_n,
        summary_batch_size=args.batch_size,
        only_new=not args.include_all,
        send_email=not args.no_email,
        html_out=None  # 每天写默认 out/daily_YYYYMMDD.html
    )

    scheduler = BlockingScheduler(timezone=tz)
    trigger = CronTrigger(hour=hh, minute=mm, timezone=tz)
    scheduler.add_job(run_partial, trigger, name="Arxiv Daily Job")

    print(f"🕒 已启动定时任务：每天 {args.time} ({args.tz}) 执行")
    print("按 Ctrl+C 退出")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 已退出定时任务")


def build_parser():
    parser = argparse.ArgumentParser(description="Arxiv-Mailbox 任务编排与调度")
    sub = parser.add_subparsers(dest="command")

    # run-once
    p1 = sub.add_parser("run-once", help="立即运行一次日报")
    p1.add_argument("--days-back", type=int, default=3, help="向前回溯天数，默认3")
    p1.add_argument("--top-n", type=int, default=10, help="发送前取TopN篇，默认10")
    p1.add_argument("--batch-size", type=int, default=3, help="DeepSeek并发批大小，默认3")
    p1.add_argument("--include-all", action="store_true", help="包含历史已处理论文（默认只推送新论文）")
    p1.add_argument("--no-email", action="store_true", help="不发送邮件，仅生成HTML")
    p1.add_argument("--html-out", type=str, default=None, help="HTML输出路径（默认 out/daily_YYYYMMDD.html）")
    p1.set_defaults(func=cmd_run_once)

    # schedule
    p2 = sub.add_parser("schedule", help="每天定时运行")
    p2.add_argument("--time", type=str, default="08:30", help="每天运行时间，HH:MM，默认08:30")
    p2.add_argument("--tz", type=str, default="Asia/Shanghai", help="时区，默认Asia/Shanghai")
    p2.add_argument("--days-back", type=int, default=3)
    p2.add_argument("--top-n", type=int, default=10)
    p2.add_argument("--batch-size", type=int, default=3)
    p2.add_argument("--include-all", action="store_true")
    p2.add_argument("--no-email", action="store_true")
    p2.set_defaults(func=cmd_schedule)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
