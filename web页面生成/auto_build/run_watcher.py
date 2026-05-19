"""
主程序入口 - 文件变更监听 + HTML 生成

用法：
    # 启动持续监控（每 30 分钟检查一次）
    python run_watcher.py

    # 仅运行一次（用于测试或手动触发）
    python run_watcher.py --once

    # 指定检查间隔（秒）
    python run_watcher.py --interval 60
"""
import argparse
import logging
import sys
from datetime import datetime

from config import OUTPUT_DIR, SOURCE_MD
from generator import HTMLGenerator
from md_parser import MarkdownParser
from watcher import FileWatcher

# --------------------------------------------------------------------------- 日志配置

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auto_build")


# --------------------------------------------------------------------------- 核心逻辑


def generate_html():
    """
    读取 Markdown → 解析 → 生成 HTML → 保存
    返回生成的文件路径列表
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    parser = MarkdownParser(str(SOURCE_MD))
    parts = parser.parse()

    if not parts:
        logger.warning("未找到任何 Part 内容，请检查 Markdown 格式")
        return []

    logger.info(f"解析完成，共 {len(parts)} 个 Part，生成时间戳：{ts}")

    # 注入所有 Part 到生成器（用于 standalone 文件的编号）
    generator = HTMLGenerator()
    generator.set_all_parts(parts)

    # 生成 HTML 文件
    files = generator.generate(parts, ts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []
    for fname, html_content in files.items():
        out_path = OUTPUT_DIR / fname
        out_path.write_text(html_content, encoding="utf-8")
        logger.info(f"  ✓ 已生成：{out_path.name}  ({len(html_content) // 1024} KB)")
        generated.append(out_path)

    return generated


# --------------------------------------------------------------------------- 入口


def main():
    parser_cli = argparse.ArgumentParser(
        description="演讲稿 → HTML 幻灯片自动生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python run_watcher.py              启动持续监控（30 分钟间隔）
  python run_watcher.py --once       仅运行一次并退出
  python run_watcher.py --interval 60   每 60 秒检查一次
        """,
    )
    parser_cli.add_argument(
        "--once",
        action="store_true",
        help="仅运行一次生成，然后退出（不持续监控）",
    )
    parser_cli.add_argument(
        "--interval",
        type=int,
        default=None,
        help="检查间隔（秒），默认 30 分钟",
    )
    args = parser_cli.parse_args()

    logger.info("=" * 50)
    logger.info("演讲稿 HTML 自动生成器")
    logger.info(f"源文件：{SOURCE_MD}")
    logger.info(f"输出目录：{OUTPUT_DIR}")
    logger.info("=" * 50)

    if args.once:
        # 单次运行模式
        logger.info("[模式] 单次运行")
        generated = generate_html()
        if generated:
            logger.info(f"生成完成，共 {len(generated)} 个文件")
        else:
            logger.warning("未生成任何文件")
        return

    # 持续监控模式
    from config import CHECK_INTERVAL_SECONDS
    interval = args.interval or CHECK_INTERVAL_SECONDS

    watcher = FileWatcher(interval_seconds=interval)

    @watcher.on_change
    def on_md_changed(is_first: bool = False):
        prefix = "首次运行" if is_first else "检测到更新"
        logger.info(f"\n{'=' * 40}\n{prefix}，正在重新生成 HTML…")
        try:
            generated = generate_html()
            if generated:
                logger.info(f"✓ 生成完成，共 {len(generated)} 个文件\n{'=' * 40}\n")
            else:
                logger.warning("未生成任何文件\n")
        except Exception as e:
            logger.error(f"生成失败：{e}", exc_info=True)

    logger.info(f"[模式] 持续监控（每 {interval // 60} 分钟检查一次）")
    logger.info("按 Ctrl+C 停止监控")
    try:
        watcher.start()
    except KeyboardInterrupt:
        logger.info("\n监控已停止")


if __name__ == "__main__":
    main()
