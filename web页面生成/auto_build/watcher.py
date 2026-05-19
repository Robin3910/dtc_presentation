"""
文件监控器 - 监听 Markdown 文件变更，触发重新生成
"""
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional

from config import CHECK_INTERVAL_SECONDS, SOURCE_MD

logger = logging.getLogger("watcher")


class FileWatcher:
    """
    监控单个 Markdown 文件的变更。

    检测原理：比较文件的 MD5 哈希值，
    哈希变化则说明文件有更新，触发回调。
    """

    def __init__(
        self,
        file_path: str = None,
        interval_seconds: int = None,
    ):
        self.file_path = Path(file_path or SOURCE_MD)
        self.interval = interval_seconds or CHECK_INTERVAL_SECONDS
        self._last_hash: Optional[str] = None
        self._on_change_callback = None

    # ------------------------------------------------------------------ 公开 API

    def on_change(self, callback):
        """
        注册变更回调：callback(part_data) -> None
        part_data 包含解析后的 Part 列表（来自 MarkdownParser）
        """
        self._on_change_callback = callback
        return callback  # 允许装饰器用法

    def start(self, run_once: bool = False):
        """
        启动监控循环。
        - run_once=True：立即执行一次，然后退出（用于测试）
        - run_once=False：正常循环监控
        """
        self._last_hash = self._compute_hash()
        logger.info(f"监控已启动：{self.file_path}（间隔 {self.interval} 秒）")

        if run_once:
            self._check_and_notify(is_first=True)
            return

        while True:
            time.sleep(self.interval)
            self._check_and_notify()

    # ------------------------------------------------------------------ 内部方法

    def _compute_hash(self) -> str:
        """计算文件的 MD5 哈希"""
        if not self.file_path.exists():
            logger.warning(f"文件不存在：{self.file_path}")
            return ""
        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    def _check_and_notify(self, is_first: bool = False):
        """检查哈希，如有变化则触发回调"""
        current_hash = self._compute_hash()
        if current_hash == self._last_hash:
            if not is_first:
                logger.debug(f"文件未变化，继续监控…")
            return

        old_hash = self._last_hash
        self._last_hash = current_hash

        if not is_first:
            logger.info(f"检测到文件变更！哈希 {old_hash[:8]}… → {current_hash[:8]}…")

        if self._on_change_callback:
            try:
                self._on_change_callback(is_first=is_first)
            except Exception as e:
                logger.error(f"回调执行失败：{e}", exc_info=True)

    def force_check(self):
        """强制检查（跳过等待间隔）"""
        self._check_and_notify()
