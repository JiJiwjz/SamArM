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
import time
import traceback
from datetime import datetime
from functools import partial

# 让本地包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import DailyJob
from src.notifier import get_notifier

# 简单日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger("main")


def cmd_run_once(args):
    notifier = get_notifier()
    start_time = time.time()
    
    try:
        # 发送启动通知
        notifier.send_job_start(args.days_back, args.top_n)
        
        job = DailyJob()
        stats = job.run(
            days_back=args.days_back,
            top_n=args.top_n,
            summary_batch_size=args.batch_size,
            only_new=not args.include_all,
            send_email=not args.no_email,
            html_out=args.html_out,
            once_per_day=args.once_per_day,
            send_at=args.send_at,
        )
        
        # 计算执行时间
        execution_time = time.time() - start_time
        
        print("\n✅ 运行完成：")
        for k, v in stats.items():
            if k not in ("email_stats", "send_result"):
                print(f"- {k}: {v}")
        if "send_result" in stats:
            print(f"- send_result: {stats['send_result']}")
        if "email_stats" in stats:
            print(f"- email_stats: {stats['email_stats']}")
        
        # 发送完成通知
        notifier.send_job_complete(stats, execution_time)
        
    except Exception as e:
        # 发送错误通知
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        notifier.send_job_error(error_msg)
        logger.error(f"任务执行失败: {e}")
        raise


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
    notifier = get_notifier()
    
    def run_with_notification():
        """带通知的运行函数"""
        start_time = time.time()
        try:
            notifier.send_job_start(args.days_back, args.top_n)
            
            stats = job.run(
                days_back=args.days_back,
                top_n=args.top_n,
                summary_batch_size=args.batch_size,
                only_new=not args.include_all,
                send_email=not args.no_email,
                html_out=None,
                once_per_day=True,
            )
            
            execution_time = time.time() - start_time
            notifier.send_job_complete(stats, execution_time)
            
        except Exception as e:
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            notifier.send_job_error(error_msg)
            logger.error(f"定时任务执行失败: {e}")

    scheduler = BlockingScheduler(timezone=tz)
    
    # 🆕 支持按天数间隔执行
    if args.interval_days > 1:
        # 每N天执行一次
        trigger = CronTrigger(hour=hh, minute=mm, day=f'*/{args.interval_days}', timezone=tz)
        print(f"🕒 已启动定时任务：每 {args.interval_days} 天 {args.time} ({args.tz}) 执行")
    else:
        # 每天执行
        trigger = CronTrigger(hour=hh, minute=mm, timezone=tz)
        print(f"🕒 已启动定时任务：每天 {args.time} ({args.tz}) 执行")
    
    scheduler.add_job(run_with_notification, trigger, name="Arxiv Daily Job")

    print("按 Ctrl+C 退出")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 已退出定时任务")


def validate_time(value):
    try:
        hh, mm = map(int, value.split(':'))
        if not 0 <= hh <= 23 or not 0 <= mm <= 59:
            raise ValueError
    except (ValueError, TypeError):
        raise argparse.ArgumentTypeError('时间必须为 HH:MM（00:00 至 23:59）')
    return f'{hh:02d}:{mm:02d}'


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
    p1.add_argument("--once-per-day", action="store_true", help="当天仅投递一次，补跑只发送尚未成功的收件人")
    p1.add_argument("--send-at", type=validate_time, default=None, help="日报提前准备，最早在此北京时间发送（HH:MM）")
    p1.set_defaults(func=cmd_run_once)

    # schedule
    p2 = sub.add_parser("schedule", help="定时运行")
    p2.add_argument("--time", type=validate_time, default="09:00", help="每天运行时间，HH:MM，默认09:00")
    p2.add_argument("--tz", type=str, default="Asia/Shanghai", help="时区，默认Asia/Shanghai")
    p2.add_argument("--days-back", type=int, default=3, help="向前回溯天数，默认3")
    p2.add_argument("--top-n", type=int, default=10, help="发送前取TopN篇，默认10")
    p2.add_argument("--batch-size", type=int, default=3, help="DeepSeek并发批大小，默认3")
    p2.add_argument("--include-all", action="store_true", help="包含历史已处理论文")
    p2.add_argument("--no-email", action="store_true", help="不发送邮件，仅生成HTML")
    p2.add_argument("--interval-days", type=int, default=1, help="🆕 执行间隔天数，默认1（每天），设置3则每3天执行一次")
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
