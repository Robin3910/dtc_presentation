"""
配置模块 - 所有路径与常量集中管理
"""
from pathlib import Path

# === 项目根目录 ===
# __file__ = .../web页面生成/auto_build/config.py
# parent   = .../web页面生成/auto_build/
# parent.parent = .../web页面生成/
# parent.parent.parent = .../dtc_presentation/  ← 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# === 源文件 ===
SOURCE_MD = PROJECT_ROOT / "演讲文稿" / "演讲内容思考记录.md"

# === 输出目录 ===
OUTPUT_DIR = PROJECT_ROOT / "web页面生成"

# === 监控间隔（秒） ===
CHECK_INTERVAL_SECONDS = 30 * 60  # 30 分钟

# === 生成配置 ===
DEFAULT_STYLE = "apple-minimal"  # 目前唯一风格，以后可扩展

# === 输出文件名格式 ===
#   {part_title}_{timestamp}.html
#   时间戳格式：YYYYMMDD_HHMMSS
OUTPUT_FILENAME_TEMPLATE = "{part_slug}_{timestamp}.html"

# === HTML 模板文件（内嵌，不依赖外部） ===
# 设计规范见 web页面生成/.claude/claude.md
