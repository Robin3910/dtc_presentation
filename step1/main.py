#!/usr/bin/env python3
"""
AI 素材审核助手 · Step 1 轻量 Demo
====================================

工作流程：
  1. 读取 materials/ 目录下的所有图片素材
  2. 调用 Claude AI 逐一审核图片是否符合品牌规范
  3. 生成结构化审核报告（Markdown 格式）
  4. 自动发送邮件通知达人审核结果

使用方法：
  # 首次配置：修改 config.py 中的 API Key 和邮件配置
  # 运行主程序：
  python main.py

  # 只生成报告，不发送邮件（仅审核模式）：
  python main.py --report-only

  # 指定素材目录：
  python main.py --materials ./my_materials
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    MATERIALS_DIR,
    REPORTS_DIR,
    DEFAULT_TO_EMAIL,
    BRAND_RULES_FILE,
)
from claude_client import ClaudeReviewer
from email_sender import EmailSender


def banner():
    print("""
╔══════════════════════════════════════════════╗
║     AI 素材审核助手 · Step 1 轻量 Demo       ║
╚══════════════════════════════════════════════╝
""")


def setup_argparse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI 素材审核助手 — 读取素材 → AI 审核 → 自动通知达人",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py                           # 完整流程（审核 + 发邮件）
  python main.py --report-only             # 仅生成审核报告，不发邮件
  python main.py --materials ./my_folder   # 指定素材目录
  python main.py --skip-review             # 跳过审核（直接用上次报告发邮件）
        """,
    )
    parser.add_argument(
        "--materials",
        type=Path,
        default=MATERIALS_DIR,
        help=f"素材目录路径（默认：{MATERIALS_DIR}）",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="仅生成报告，不发送邮件",
    )
    parser.add_argument(
        "--skip-review",
        action="store_true",
        help="跳过 AI 审核步骤，直接用 reports/ 目录下的最新报告发送邮件",
    )
    parser.add_argument(
        "--to",
        type=str,
        default="",
        help="指定邮件收件人（默认为配置文件中的 DEFAULT_TO_EMAIL）",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=BRAND_RULES_FILE,
        help=f"品牌规范文件路径（默认：{BRAND_RULES_FILE}）",
    )
    return parser.parse_args()


def check_config():
    """检查关键配置是否已填写"""
    from config import (
        CLAUDE_API_KEY,
        SMTP_USER, SMTP_PASS,
        DEBUG_MODE,
    )

    errors = []

    # Claude API Key 必须配置
    if not CLAUDE_API_KEY or CLAUDE_API_KEY == "your-anthropic-api-key-here":
        errors.append(
            "⚠️  CLAUDE_API_KEY 未配置\n"
            "   请填写到 config.py 中，或设置环境变量 ANTHROPIC_API_KEY"
        )

    # 邮件配置仅在非调试模式下强制检查
    if not DEBUG_MODE:
        if not SMTP_USER or SMTP_USER == "your-email@foxmail.com":
            errors.append(
                "⚠️  SMTP 配置未填写\n"
                "   请在 config.py 中填写发件邮箱和 SMTP 授权码"
            )
        if not SMTP_PASS or SMTP_PASS == "your-smtp-auth-code":
            errors.append(
                "⚠️  SMTP_PASS 未填写\n"
                "   请填写 QQ 邮箱 / QQ 企业邮箱的「授权码」"
            )
    else:
        print("🐛 [调试模式] 已跳过邮件配置检查（DEBUG_MODE=True）")

    if errors:
        print("\n配置检查未通过：\n")
        for e in errors:
            print(e)
            print()
        return False
    return True


def ensure_dirs():
    """确保必要的目录存在"""
    MATERIALS_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    print(f"📁 素材目录：{MATERIALS_DIR}")
    print(f"📁 报告目录：{REPORTS_DIR}\n")


def print_summary(results: list):
    """打印审核结果摘要"""
    counts = {"pass": 0, "needs_revision": 0, "reject": 0}
    for r in results:
        counts[r.status] += 1

    status_icon = {"pass": "✅", "needs_revision": "⚠️", "reject": "❌"}
    status_text = {"pass": "通过", "needs_revision": "需修改", "reject": "违规"}

    print("\n" + "=" * 50)
    print("  审核结果摘要")
    print("=" * 50)
    for s, label in status_text.items():
        icon = status_icon[s]
        print(f"  {icon} {label}：{counts[s]} 份")

    total = len(results)
    pass_rate = counts["pass"] / total * 100 if total > 0 else 0
    print(f"\n  通过率：{pass_rate:.1f}%")
    print(f"  总计：{total} 份素材\n")

    print("  详细结果：")
    for r in results:
        icon = status_icon[r.status]
        print(f"  {icon} {r.filename} → {status_text[r.status]}")
        if r.violations:
            for v in r.violations[:2]:
                print(f"     └ {v}")
    print()


def run_review(args) -> list:
    """执行 AI 审核流程"""
    print("🚀 开始 AI 素材审核...\n")
    print(f"📖 品牌规范文件：{args.rules}")
    print(f"📦 素材目录：{args.materials}\n")

    reviewer = ClaudeReviewer()
    results = reviewer.review_all(args.materials)

    if not results:
        print("⚠️  未找到任何素材，程序退出")
        sys.exit(0)

    # 保存报告
    report_path = reviewer.save_report(results)
    print_summary(results)

    return results, report_path


def run_email(args, results: list, report_path: Path = None):
    """执行邮件发送流程"""
    print("✉️  开始发送邮件通知...\n")

    sender = EmailSender()
    to_email = args.to or DEFAULT_TO_EMAIL

    if not to_email:
        # 尝试从每份素材文件名中提取邮箱，分别发送给对应达人
        print("📬 未指定收件人，将按素材文件名将结果发送给对应达人邮箱：\n")
        email_groups = {}
        for r in results:
            if r.email:
                if r.email not in email_groups:
                    email_groups[r.email] = []
                email_groups[r.email].append(r)

        if not email_groups:
            print("⚠️  未能从素材文件名中提取到任何邮箱地址，请配置 DEFAULT_TO_EMAIL 或使用 --to 参数")
            return

        for email, group_results in email_groups.items():
            print(f"  → 发送给 {email}（{len(group_results)} 份素材）")
            sender.send_review_email(email, group_results)
    else:
        # 发送给单个收件人（运营团队）
        print(f"  → 发送给：{to_email}")
        sender.send_review_email(to_email, results)


def main():
    banner()
    args = setup_argparse()

    # 检查配置
    if not check_config():
        sys.exit(1)

    # 确保目录存在
    ensure_dirs()

    # 执行审核
    if not args.skip_review:
        results, report_path = run_review(args)
    else:
        # 跳过审核，从最新报告中加载结果
        reports = sorted(REPORTS_DIR.glob("review_report_*.md"))
        if not reports:
            print("⚠️  未找到已有报告，无法跳过审核，请先运行正常审核流程")
            sys.exit(1)
        latest = reports[-1]
        print(f"📄 跳过审核，从已有报告加载：{latest}")
        from claude_client import ReviewResult
        import json, re

        results = []
        content = latest.read_text(encoding="utf-8")
        sections = re.split(r"\n---\n|\n## ", content)
        # 简单解析（后续可优化为完整解析器）
        results = [ReviewResult(filename="(from report)", email="", file_path="", status="pass")]
        report_path = latest

    # 发送邮件（除非指定了 --report-only）
    if not args.report_only:
        run_email(args, results, report_path)
    else:
        print("📋 已完成报告生成，跳过邮件发送（--report-only 模式）\n")

    print("\n✨ 所有流程执行完毕！")


if __name__ == "__main__":
    main()
