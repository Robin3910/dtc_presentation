# -*- coding: utf-8 -*-
"""
邮件发送模块：审核完成后自动向达人发送结果通知邮件
"""

import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASS,
    SENDER_EMAIL,
    SENDER_NAME,
    DEBUG_MODE,
)

logger = logging.getLogger(__name__)


class ReviewResult:
    """邮件发送所需的审核结果格式（兼容 Step 1）"""
    def __init__(self, filename, email, file_path, status, violations=None, suggestions=None, notes=None, raw_response=""):
        self.filename = filename
        self.email = email
        self.file_path = file_path
        self.status = status
        self.violations = violations or []
        self.suggestions = suggestions or []
        self.notes = notes or []
        self.raw_response = raw_response


class EmailSender:
    """邮件发送器，支持 QQ 邮箱 / QQ 企业邮箱"""

    def __init__(self):
        self.host = SMTP_HOST
        self.port = SMTP_PORT
        self.user = SMTP_USER
        self.password = SMTP_PASS
        self.sender_email = SENDER_EMAIL
        self.sender_name = SENDER_NAME

    def _build_body(self, results: List[ReviewResult]) -> tuple:
        """生成邮件正文（纯文本 + HTML 两个版本）"""

        counts = {"pass": 0, "needs_revision": 0, "reject": 0}
        for r in results:
            counts[r.status] += 1

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ── HTML 版本 ─────────────────────────────────────
        status_color = {
            "pass": "#22c55e",
            "needs_revision": "#f59e0b",
            "reject": "#ef4444",
        }
        status_label = {"pass": "✅ 通过", "needs_revision": "⚠️ 需修改", "reject": "❌ 违规"}
        status_icon = {"pass": "✅", "needs_revision": "⚠️", "reject": "❌"}

        rows = ""
        for r in results:
            color = status_color[r.status]
            label = status_label[r.status]
            icon = status_icon[r.status]
            violations_html = (
                "<br>".join(f"• {v}" for v in r.violations)
                if r.violations
                else "无"
            )
            suggestions_html = (
                "<br>".join(f"• {s}" for s in r.suggestions)
                if r.suggestions
                else "无"
            )
            rows += f"""
        <tr>
          <td>{r.filename}</td>
          <td><span style="color:{color};font-weight:bold">{label}</span></td>
          <td>{violations_html}</td>
          <td>{suggestions_html}</td>
        </tr>"""

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f4f4f5; margin:0; padding:20px; }}
  .card {{ background:white; border-radius:12px; padding:32px; max-width:700px; margin:0 auto; box-shadow:0 2px 12px rgba(0,0,0,0.08); }}
  h1 {{ color:#1a1a1a; font-size:20px; margin:0 0 8px; }}
  .subtitle {{ color:#666; font-size:14px; margin:0 0 24px; }}
  .summary {{ display:flex; gap:12px; margin-bottom:24px; }}
  .badge {{ flex:1; padding:12px 16px; border-radius:8px; text-align:center; font-size:14px; font-weight:600; }}
  .badge.green {{ background:#f0fdf4; color:#16a34a; }}
  .badge.yellow {{ background:#fefce8; color:#ca8a04; }}
  .badge.red {{ background:#fef2f2; color:#dc2626; }}
  table {{ width:100%; border-collapse:collapse; font-size:14px; }}
  th {{ text-align:left; background:#f9f9f9; padding:10px 12px; border-bottom:2px solid #eee; color:#333; }}
  td {{ padding:10px 12px; border-bottom:1px solid #f0f0f0; vertical-align:top; }}
  .footer {{ margin-top:24px; padding-top:16px; border-top:1px solid #eee; color:#999; font-size:12px; text-align:center; }}
</style>
</head>
<body>
<div class="card">
  <h1>📋 素材审核结果通知</h1>
  <p class="subtitle">审核时间：{timestamp} &nbsp;|&nbsp; 共审核 {len(results)} 份素材</p>

  <div class="summary">
    <div class="badge green">✅ 通过 {counts['pass']} 份</div>
    <div class="badge yellow">⚠️ 需修改 {counts['needs_revision']} 份</div>
    <div class="badge red">❌ 违规 {counts['reject']} 份</div>
  </div>

  <table>
    <thead>
      <tr>
        <th>素材名称</th>
        <th>审核结果</th>
        <th>违规条款</th>
        <th>修改建议</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>

  <div class="footer">
    此邮件由 AI 素材审核助手自动发送 · 请勿直接回复<br>
    如有疑问请联系运营团队
  </div>
</div>
</body>
</html>"""

        # ── 纯文本版本 ──────────────────────────────────────
        plain_lines = [
            f"素材审核结果通知",
            f"审核时间：{timestamp}",
            f"共审核 {len(results)} 份素材",
            "",
            "审核摘要：",
            f"  ✅ 通过：{counts['pass']} 份",
            f"  ⚠️ 需修改：{counts['needs_revision']} 份",
            f"  ❌ 违规：{counts['reject']} 份",
            "",
            "详细结果：",
        ]
        for r in results:
            icon = status_icon[r.status]
            label = status_label[r.status]
            plain_lines.append(f"  {icon} {r.filename} → {label}")
            if r.violations:
                for v in r.violations:
                    plain_lines.append(f"     违规：{v}")
            if r.suggestions:
                for s in r.suggestions:
                    plain_lines.append(f"     建议：{s}")
            plain_lines.append("")

        plain_lines.append("此邮件由 AI 素材审核助手自动发送，如有疑问请联系运营团队。")

        return "\n".join(plain_lines), html

    def send_review_email(
        self,
        to_email: str,
        results: List[ReviewResult],
        subject: str = "",
    ) -> bool:
        """向达人发送审核结果邮件"""
        if not to_email:
            logger.warning("未提供收件人邮箱，跳过发送")
            return False

        if not subject:
            pass_count = sum(1 for r in results if r.status == "pass")
            revision_count = sum(1 for r in results if r.status == "needs_revision")
            reject_count = sum(1 for r in results if r.status == "reject")
            subject = f"📋 素材审核完成 — {pass_count}份通过 / {revision_count}份需修改 / {reject_count}份违规"

        plain_body, html_body = self._build_body(results)

        # ── 调试模式：打印邮件内容，不真实发送 ───────────────────
        if DEBUG_MODE:
            logger.info(f"\n  🐛 [调试模式] 邮件内容预览 → {to_email}")
            logger.info(f"  ── 主题：{subject}")
            logger.info(f"  ── 纯文本预览：")
            for line in plain_body.split("\n")[:20]:
                logger.info(f"      {line}")
            logger.info("      ...（略）\n")
            return True

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.sender_email}>"
        msg["To"] = to_email

        msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                server.login(self.user, self.password)
                server.sendmail(self.sender_email, [to_email], msg.as_string())
            logger.info(f"✉️  邮件已发送至：{to_email}")
            return True
        except Exception as e:
            logger.error(f"⚠️  邮件发送失败：{e}")
            return False

    def send_batch_summary(
        self,
        all_results: List[ReviewResult],
        default_to: str = "",
    ) -> None:
        """将审核结果汇总发送给默认收件人（运营团队）"""
        if not default_to:
            logger.warning("未配置 DEFAULT_TO_EMAIL，跳过汇总邮件发送")
            return

        self.send_review_email(default_to, all_results, subject="📊 素材审核日报")
