# -*- coding: utf-8 -*-
"""
数据库模块：使用 SQLite 存储审核记录
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from config import DB_PATH


class Database:
    """审核记录数据库管理器"""

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 素材表：存储上传的素材信息
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    cloud_path TEXT,
                    file_size INTEGER,
                    mime_type TEXT,
                    uploader_email TEXT,
                    uploader_name TEXT,
                    upload_time TEXT NOT NULL,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'uploading', 'uploaded', 'reviewing', 'reviewed', 'deleted')),
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 审核记录表：存储审核结果
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    material_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    reviewer_result TEXT CHECK(reviewer_result IN ('pass', 'needs_revision', 'reject')),
                    violations TEXT,  -- JSON 格式存储违规条款列表
                    suggestions TEXT,  -- JSON 格式存储修改建议列表
                    notes TEXT,
                    raw_response TEXT,
                    review_time TEXT NOT NULL,
                    reviewer_model TEXT,
                    email_sent INTEGER DEFAULT 0,
                    email_sent_time TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (material_id) REFERENCES materials(id)
                )
            """)

            # 通知记录表：存储邮件发送记录
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id INTEGER NOT NULL,
                    material_id INTEGER NOT NULL,
                    recipient_email TEXT NOT NULL,
                    notification_type TEXT CHECK(notification_type IN ('creator', 'operation')),
                    sent_time TEXT NOT NULL,
                    status TEXT DEFAULT 'success' CHECK(status IN ('success', 'failed')),
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (review_id) REFERENCES reviews(id),
                    FOREIGN KEY (material_id) REFERENCES materials(id)
                )
            """)

            # 操作日志表：记录关键操作
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    operator TEXT,
                    target_id INTEGER,
                    target_type TEXT,
                    details TEXT,
                    ip_address TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引以提升查询性能
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_materials_upload_time ON materials(upload_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_material_id ON reviews(material_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_review_time ON reviews(review_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_material_id ON notifications(material_id)")

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ── 素材管理 ─────────────────────────────────────────────

    def add_material(
        self,
        filename: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        mime_type: str,
        uploader_email: str = "",
        uploader_name: str = "",
    ) -> int:
        """添加新素材记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO materials 
                (filename, original_filename, file_path, file_size, mime_type, 
                 uploader_email, uploader_name, upload_time, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (filename, original_filename, file_path, file_size, mime_type,
                 uploader_email, uploader_name, datetime.now().isoformat()),
            )
            conn.commit()
            return cursor.lastrowid

    def update_material_status(self, material_id: int, status: str, cloud_path: str = None):
        """更新素材状态"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if cloud_path:
                cursor.execute(
                    "UPDATE materials SET status = ?, cloud_path = ?, updated_at = ? WHERE id = ?",
                    (status, cloud_path, datetime.now().isoformat(), material_id),
                )
            else:
                cursor.execute(
                    "UPDATE materials SET status = ?, updated_at = ? WHERE id = ?",
                    (status, datetime.now().isoformat(), material_id),
                )
            conn.commit()

    def delete_material(self, material_id: int):
        """删除素材及其关联的审核记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 先删除关联的审核记录
            cursor.execute("DELETE FROM reviews WHERE material_id = ?", (material_id,))
            # 再删除素材记录
            cursor.execute("DELETE FROM materials WHERE id = ?", (material_id,))
            conn.commit()

    def get_material(self, material_id: int) -> Optional[Dict[str, Any]]:
        """获取单个素材信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_materials(
        self,
        status: str = None,
        limit: int = 100,
        offset: int = 0,
        uploader_email: str = None,
    ) -> List[Dict[str, Any]]:
        """获取素材列表（支持过滤和分页）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM materials WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if uploader_email:
                query += " AND uploader_email = ?"
                params.append(uploader_email)

            query += " ORDER BY upload_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_pending_materials(self) -> List[Dict[str, Any]]:
        """获取待审核的素材列表"""
        return self.get_materials(status="uploaded")

    def get_material_count(self, status: str = None) -> int:
        """获取素材总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT COUNT(*) FROM materials WHERE status = ?", (status,))
            else:
                cursor.execute("SELECT COUNT(*) FROM materials")
            return cursor.fetchone()[0]

    # ── 审核记录管理 ─────────────────────────────────────────

    def add_review(
        self,
        material_id: int,
        filename: str,
        reviewer_result: str,
        violations: List[str],
        suggestions: List[str],
        notes: str = "",
        raw_response: str = "",
        reviewer_model: str = "",
    ) -> int:
        """添加审核记录"""
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 确保所有类型正确：violations, suggestions, notes 必须是字符串
            violations_json = json.dumps(violations, ensure_ascii=False) if isinstance(violations, (list, tuple)) else str(violations) if violations else "[]"
            suggestions_json = json.dumps(suggestions, ensure_ascii=False) if isinstance(suggestions, (list, tuple)) else str(suggestions) if suggestions else "[]"
            notes_str = json.dumps(notes, ensure_ascii=False) if isinstance(notes, (list, tuple)) else str(notes) if notes else ""
            
            cursor.execute(
                """
                INSERT INTO reviews 
                (material_id, filename, reviewer_result, violations, suggestions, 
                 notes, raw_response, review_time, reviewer_model)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (material_id, filename, reviewer_result, violations_json,
                 suggestions_json, notes_str, raw_response,
                 datetime.now().isoformat(), reviewer_model),
            )
            conn.commit()
            return cursor.lastrowid

    def get_review(self, material_id: int) -> Optional[Dict[str, Any]]:
        """获取素材的审核结果"""
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM reviews WHERE material_id = ? ORDER BY review_time DESC LIMIT 1",
                (material_id,),
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["violations"] = json.loads(result["violations"] or "[]")
                result["suggestions"] = json.loads(result["suggestions"] or "[]")
                result["notes"] = json.loads(result.get("notes") or "[]")
                return result
            return None

    def get_reviews(
        self,
        material_ids: List[int] = None,
        result: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """获取审核记录列表"""
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT r.*, m.filename, m.original_filename, m.uploader_email, m.upload_time
                FROM reviews r
                JOIN materials m ON r.material_id = m.id
                WHERE 1=1
            """
            params = []

            if material_ids:
                query += f" AND r.material_id IN ({','.join(['?'] * len(material_ids))})"
                params.extend(material_ids)
            if result:
                query += " AND r.reviewer_result = ?"
                params.append(result)
            if start_date:
                query += " AND r.review_time >= ?"
                params.append(start_date)
            if end_date:
                query += " AND r.review_time <= ?"
                params.append(end_date)

            query += " ORDER BY r.review_time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                result_dict = dict(row)
                result_dict["violations"] = json.loads(result_dict["violations"] or "[]")
                result_dict["suggestions"] = json.loads(result_dict["suggestions"] or "[]")
                result_dict["notes"] = json.loads(result_dict.get("notes") or "[]")
                results.append(result_dict)
            return results

    def mark_review_email_sent(self, review_id: int):
        """标记审核结果邮件已发送"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reviews SET email_sent = 1, email_sent_time = ? WHERE id = ?",
                (datetime.now().isoformat(), review_id),
            )
            conn.commit()

    # ── 通知记录管理 ─────────────────────────────────────────

    def add_notification(
        self,
        review_id: int,
        material_id: int,
        recipient_email: str,
        notification_type: str,
        status: str = "success",
        error_message: str = "",
    ):
        """添加通知发送记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notifications 
                (review_id, material_id, recipient_email, notification_type, sent_time, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (review_id, material_id, recipient_email, notification_type,
                 datetime.now().isoformat(), status, error_message),
            )
            conn.commit()
            return cursor.lastrowid

    # ── 统计数据 ─────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 总素材数
            cursor.execute("SELECT COUNT(*) FROM materials")
            total_materials = cursor.fetchone()[0]
            
            # 各状态素材数
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM materials 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 审核结果统计
            cursor.execute("""
                SELECT reviewer_result, COUNT(*) as count 
                FROM reviews 
                GROUP BY reviewer_result
            """)
            review_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 今日数据
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT COUNT(*) FROM materials WHERE date(upload_time) = ?",
                (today,),
            )
            today_uploads = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM reviews WHERE date(review_time) = ?",
                (today,),
            )
            today_reviews = cursor.fetchone()[0]
            
            # 邮件发送统计
            cursor.execute(
                "SELECT COUNT(*) FROM reviews WHERE email_sent = 1 AND date(email_sent_time) = ?",
                (today,),
            )
            today_emails_sent = cursor.fetchone()[0]

            return {
                "total_materials": total_materials,
                "status_counts": status_counts,
                "review_counts": review_counts,
                "today_uploads": today_uploads,
                "today_reviews": today_reviews,
                "today_emails_sent": today_emails_sent,
            }

    # ── 操作日志 ─────────────────────────────────────────────

    def add_log(
        self,
        operation_type: str,
        operator: str = "",
        target_id: int = None,
        target_type: str = "",
        details: str = "",
        ip_address: str = "",
    ):
        """添加操作日志"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 确保所有值都是可序列化的
            target_id_value = target_id if isinstance(target_id, int) else None
            operator_str = str(operator) if operator else ""
            details_str = str(details) if details else ""
            ip_address_str = str(ip_address) if ip_address else ""
            cursor.execute(
                """
                INSERT INTO operation_logs 
                (operation_type, operator, target_id, target_type, details, ip_address)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (operation_type, operator_str, target_id_value, target_type, details_str, ip_address_str),
            )
            conn.commit()
