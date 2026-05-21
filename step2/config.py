# -*- coding: utf-8 -*-
"""
Step 2 配置文件：AI 素材审核助手 · 完整系统
=============================================

首次部署请填写以下配置项

使用方法：
  # 开发环境
  python app.py

  # 生产环境（推荐使用 systemd 管理）
  nohup python app.py --prod > logs/app.log 2>&1 &
"""

import os
import sys
from pathlib import Path

# ── 基础路径配置 ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"        # 本地上传临时目录（最终会同步到云存储）
REPORTS_DIR = BASE_DIR / "reports"        # 生成的审核报告目录
LOGS_DIR = BASE_DIR / "logs"              # 日志目录
TEMPLATES_DIR = BASE_DIR / "templates"   # 前端模板目录

# 确保必要目录存在
UPLOADS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

# ── 服务器配置 ─────────────────────────────────────────────
HOST = os.getenv("APP_HOST", "0.0.0.0")
PORT = int(os.getenv("APP_PORT", "8080"))
DEBUG_MODE = os.getenv("APP_DEBUG", "true").lower() == "true"

# ── Flask 安全配置 ──────────────────────────────────────────
# 用于签名 session cookie，生产环境请使用随机字符串
SECRET_KEY = os.getenv("SECRET_KEY", "ai-reviewer-secret-key-change-in-production")

# ── AI 审核配置 ─────────────────────────────────────────────
# DMXAPI 中转站配置（用于图片分析）
DMXAPI_BASE_URL = os.getenv("DMXAPI_BASE_URL", "https://www.dmxapi.cn")
DMXAPI_API_KEY = os.getenv("DMXAPI_API_KEY", "sk-Zun61an7Wu5axwgj3LeodrHIWmw0OZVDGYkpvbfO4z8Wz7DN")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "kimi-k2.6")

# 品牌规范文件
BRAND_RULES_FILE = BASE_DIR.parent / "step1" / "brand_rules.md"

# 审核任务调度配置
REVIEW_INTERVAL_MINUTES = int(os.getenv("REVIEW_INTERVAL", "1"))  # 每隔多少分钟扫描一次新素材
ENABLE_AUTO_REVIEW = os.getenv("ENABLE_AUTO_REVIEW", "true").lower() == "true"

# ── 云存储配置（腾讯云 COS）────────────────────────────────
# 文档：https://cloud.tencent.com/document/product/436
USE_CLOUD_STORAGE = os.getenv("USE_CLOUD_STORAGE", "false").lower() == "true"
# USE_CLOUD_STORAGE = "false"

COS_CONFIG = {
    "enabled": USE_CLOUD_STORAGE,
    "provider": os.getenv("COS_PROVIDER", "tencent"),  # "tencent" | "aliyun"
    
    # 腾讯云 COS 配置
    "tencent": {
        "secret_id": os.getenv("TENCENT_SECRET_ID", ""),
        "secret_key": os.getenv("TENCENT_SECRET_KEY", ""),
        "region": os.getenv("TENCENT_COS_REGION", "ap-guangzhou"),
        "bucket": os.getenv("TENCENT_COS_BUCKET", ""),
        "prefix": os.getenv("TENCENT_COS_PREFIX", "materials/"),  # 云端素材路径前缀
    },
    
    # 阿里云 OSS 配置
    "aliyun": {
        "access_key_id": os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
        "access_key_secret": os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
        "endpoint": os.getenv("ALIYUN_OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com"),
        "bucket": os.getenv("ALIYUN_OSS_BUCKET", ""),
        "prefix": os.getenv("ALIYUN_OSS_PREFIX", "materials/"),
    }
}

# ── 数据库配置 ─────────────────────────────────────────────
# 使用 SQLite 作为本地数据库（轻量、无需额外安装）
DB_PATH = BASE_DIR / "review.db"

# ── 邮件发送配置 ─────────────────────────────────────────────
EMAIL_MODE = "qq"  # "qq" = 个人QQ邮箱 / "exmail" = QQ企业邮箱

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your-email@foxmail.com")
SENDER_NAME = os.getenv("SENDER_NAME", "AI 素材审核助手")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.exmail.qq.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER", "your-email@foxmail.com")
SMTP_PASS = os.getenv("SMTP_PASS", "your-smtp-auth-code")

# 运营团队通知邮箱（审核结果通知发送给运营）
OPERATION_TEAM_EMAIL = os.getenv("OPERATION_TEAM_EMAIL", "")

# ── 管理后台认证配置 ─────────────────────────────────────────
# 简单密码保护（生产环境建议使用更复杂的认证）
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # 部署时请修改！

# ── 上传配置 ─────────────────────────────────────────────
# 允许的文件类型
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "avi"}
# 单个文件最大大小（MB）
MAX_FILE_SIZE_MB = 50
# 单次上传最大文件数
MAX_FILES_PER_UPLOAD = 10

# ── 报告配置 ─────────────────────────────────────────────
REPORT_FORMAT = "markdown"  # "markdown" | "json"
