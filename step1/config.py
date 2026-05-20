"""
配置文件：存放所有密钥和服务配置
首次使用请填写以下配置项
"""

import os
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
MATERIALS_DIR = BASE_DIR / "materials"       # 达人素材存放目录
REPORTS_DIR  = BASE_DIR / "reports"          # 生成的审核报告存放目录

# ── Claude API 配置 ─────────────────────────────────────────
# 优先使用环境变量 / 中转 API，备选官方直连
CLAUDE_API_BASE_URL = os.getenv("ANTHROPIC_API_BASE_URL", "https://apinebula.com/v1")
CLAUDE_API_KEY     = os.getenv("ANTHROPIC_API_KEY", "sk-7CsKSA3Mq3YWM78bjA7aa0guigOURdWQaQnFAM52JTNPWzzq")
CLAUDE_MODEL       = "claude-sonnet-4-20250514"  # 或 claude-3-5-sonnet-latest

# ── 邮件发送配置 ───────────────────────────────────────────
# 支持两种模式：QQ 邮箱 / QQ 企业邮箱（exmail）
EMAIL_MODE = "qq"          # "qq" = 个人QQ邮箱 / "exmail" = QQ企业邮箱

# ── 调试模式 ───────────────────────────────────────────────
# 设为 True 时跳过真实邮件发送，仅在终端打印邮件内容，方便测试流程
DEBUG_MODE = True          # 调试阶段设为 True，完成配置后改为 False

# 发件人账号
SENDER_EMAIL = "your-email@foxmail.com"
SENDER_NAME  = "AI 素材审核助手"

# SMTP 配置（QQ 邮箱 / QQ 企业邮箱）
SMTP_HOST = "smtp.exmail.qq.com"   # QQ企业邮箱用 smtp.exmail.qq.com
SMTP_PORT = 465                    # SSL 端口
SMTP_USER = "your-email@foxmail.com"
SMTP_PASS = "your-smtp-auth-code"  # QQ邮箱/企业邮箱的「授权码」

# 收件人（留空则从素材文件名中提取邮箱）
# 示例：DEFAULT_TO_EMAIL = "operation-team@example.com"
DEFAULT_TO_EMAIL = ""

# ── 品牌规范文件 ───────────────────────────────────────────
BRAND_RULES_FILE = BASE_DIR / "brand_rules.md"

# ── 报告配置 ───────────────────────────────────────────────
REPORT_FORMAT = "markdown"   # "markdown" | "json"
