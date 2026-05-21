#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI 素材审核助手 · Step 2 完整系统
====================================

Web 服务器 + AI 审核调度器 + 管理后台

功能特性：
- 🌐 Web 上传页面（达人自助上传）
- 🤖 AI 自动审核（定时扫描 + 手动触发）
- 📧 邮件自动通知（达人 + 运营团队）
- ☁️ 云存储集成（腾讯云 COS / 阿里云 OSS）
- 📊 管理后台（数据统计、素材管理、审核记录）

使用方法：
  # 开发环境
  python app.py

  # 生产环境
  python app.py --prod

  # 只启动 Web 服务（不启动调度器）
  python app.py --web-only

  # 手动触发审核
  python app.py --trigger-review
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask
from flask_cors import CORS

from config import (
    HOST, PORT, DEBUG_MODE, TEMPLATES_DIR,
    ENABLE_AUTO_REVIEW, REPORTS_DIR, LOGS_DIR,
    SECRET_KEY,
)
from routes import main_bp, api_bp, init_scheduler
from review_scheduler import ReviewScheduler
from database import Database


def setup_logging(prod: bool = False):
    """配置日志"""
    LOGS_DIR.mkdir(exist_ok=True)
    
    log_level = logging.INFO if prod else logging.DEBUG
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    if prod:
        # 生产环境：同时输出到文件和控制台
        file_handler = logging.FileHandler(
            LOGS_DIR / "app.log",
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # 控制台只显示警告以上
        console_handler.setFormatter(logging.Formatter(log_format))
        
        logging.basicConfig(
            level=log_level,
            handlers=[file_handler, console_handler]
        )
    else:
        # 开发环境：输出到控制台
        logging.basicConfig(
            level=log_level,
            format=log_format
        )


def create_app() -> Flask:
    """创建 Flask 应用"""
    app = Flask(
        "AI素材审核助手",
        template_folder=str(TEMPLATES_DIR),
    )
    
    # 设置 Secret Key（用于签名 session cookie）
    app.secret_key = SECRET_KEY
    
    # 启用 CORS（允许跨域访问 API）
    CORS(app)
    
    # 注册蓝图
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # 初始化数据库
    db = Database()
    logging.info("✅ 数据库初始化完成")
    
    return app


def start_scheduler():
    """启动审核调度器"""
    scheduler = ReviewScheduler()
    if ENABLE_AUTO_REVIEW:
        scheduler.start()
        logging.info("✅ 自动审核调度器已启动")
    else:
        logging.info("⚠️  自动审核功能未启用（ENABLE_AUTO_REVIEW=False）")
    
    # 将调度器注册到路由
    init_scheduler(scheduler)
    return scheduler


def print_banner():
    """打印启动Banner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║       AI 素材审核助手 · Step 2 完整系统                  ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║   🌐 Web 服务：http://localhost:{port}                      ║
║   📤 上传页面：http://localhost:{port}/                     ║
║   🔐 管理后台：http://localhost:{port}/admin                 ║
║                                                          ║
║   按 Ctrl+C 停止服务                                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
    """.format(port=PORT))


def main():
    parser = argparse.ArgumentParser(
        description="AI 素材审核助手 — Web 服务 + AI 审核调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python app.py                           # 完整启动（Web + 调度器）
  python app.py --prod                    # 生产环境启动
  python app.py --web-only                # 仅启动 Web 服务
  python app.py --port 9000               # 指定端口
        """,
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="生产环境模式（禁用调试，优化日志）",
    )
    parser.add_argument(
        "--web-only",
        action="store_true",
        help="仅启动 Web 服务，不启动审核调度器",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=PORT,
        help=f"服务端口（默认：{PORT}）",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=HOST,
        help=f"监听地址（默认：{HOST}）",
    )
    parser.add_argument(
        "--trigger-review",
        action="store_true",
        help="手动触发所有待审核素材的审核",
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging(args.prod)
    
    # 创建应用
    app = create_app()
    
    # 启动调度器
    scheduler = None
    if not args.web_only:
        scheduler = start_scheduler()
    
    # 手动触发审核
    if args.trigger_review:
        if scheduler:
            scheduler.trigger_review_all()
        else:
            db = Database()
            scheduler = ReviewScheduler()
            scheduler.trigger_review_all()
        return
    
    # 打印Banner
    print_banner()
    
    # 启动服务
    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=not args.prod,
            threaded=True,
        )
    except KeyboardInterrupt:
        logging.info("\n👋 服务已停止")
        if scheduler:
            scheduler.stop()


if __name__ == "__main__":
    main()
