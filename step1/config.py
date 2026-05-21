# -*- coding: utf-8 -*-
"""
配置文件：存放所有密钥和服务配置
首次使用请填写以下配置项
"""

import os
import sys
from pathlib import Path

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
MATERIALS_DIR = BASE_DIR / "materials"       # 达人素材存放目录
REPORTS_DIR  = BASE_DIR / "reports"          # 生成的审核报告存放目录

# DeepSeek（推荐，便宜快速）：用于纯文本对话（不支持图片）
# 视觉审核（带图）必须走 Claude
DEEPSEEK_API_KEY     = os.getenv("DEEPSEEK_API_KEY", "sk-6e9ada949b7c420080e23976f2183128")
DEEPSEEK_API_BASE    = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_MODEL       = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")  # 仅文本，不支持图片

# DMXAPI 中转站配置（用于图片分析）
# 官网：https://doc.dmxapi.cn
# API Key 优先级：环境变量 > 代码配置
# 注意：base_url 只填域名，代码会自动拼接 /v1/messages
DMXAPI_BASE_URL = os.getenv("DMXAPI_BASE_URL", "https://www.dmxapi.cn")
DMXAPI_API_KEY  = os.getenv("DMXAPI_API_KEY", "sk-Zun61an7Wu5axwgj3LeodrHIWmw0OZVDGYkpvbfO4z8Wz7DN")

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "kimi-k2.6")

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
