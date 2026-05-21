# -*- coding: utf-8 -*-
"""
AI 审核调度器：定时扫描新素材并触发审核流程
"""

import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import base64

from config import (
    DMXAPI_API_KEY,
    DMXAPI_BASE_URL,
    CLAUDE_MODEL,
    BRAND_RULES_FILE,
    REPORTS_DIR,
    ENABLE_AUTO_REVIEW,
    REVIEW_INTERVAL_MINUTES,
)
from database import Database
from cloud_storage import get_storage_instance
from email_sender import EmailSender

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """单份素材的审核结果"""
    material_id: int
    filename: str
    uploader_email: str
    status: str  # "pass", "needs_revision", "reject"
    violations: List[str]
    suggestions: List[str]
    notes: List[str]
    raw_response: str


class AIReviewer:
    """AI 审核器 - 使用 DMXAPI 调用 Claude 进行图片审核"""

    SYSTEM_PROMPT = """你是一位专业的品牌内容审核专家，专注于vivo手机的达人素材审核。

你的职责：
1. 严格依据品牌规范，对达人提交的素材（图片/视频截图）进行合规性审核
2. 输出结构化的审核报告，标注每条违规内容和修改建议
3. 对合规素材给出正面反馈和改进建议

输出要求：
- 每份素材必须给出明确的审核结论：通过 / 需修改 / 违规
- 逐条列出违规内容和对应的规范条款
- 对「需修改」的素材，提供具体的修改建议和参考话术
- 审核标准严格执行 brand_rules.md 中的所有条款，不得放宽

请用简体中文输出审核报告。"""

    def __init__(self):
        self.api_key = DMXAPI_API_KEY
        self.base_url = DMXAPI_BASE_URL.rstrip("/")
        self.model = CLAUDE_MODEL
        
        try:
            self.rules_text = BRAND_RULES_FILE.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(f"⚠️  品牌规范文件不存在：{BRAND_RULES_FILE}，将使用默认规范")
            self.rules_text = "请严格按照品牌规范进行审核。"

        self.headers = {
            "content-type": "application/json",
            "x-api-key": self.api_key,
        }

    def _build_user_prompt(self, filename: str) -> str:
        return f"""## 待审核素材

素材文件名：{filename}

---

## 品牌审核规范

请严格按照以下规范进行审核：

{self.rules_text}

---

## 审核要求

请仔细分析图片内容，逐一对照品牌规范进行合规性检查，并输出以下格式的审核报告：

首先，要解释图片的内容是什么。包含了什么文字，图片的内容。

### 素材：{filename}

**审核结论：** ✅ 通过 / ⚠️ 需修改 / ❌ 违规

**违规条款（若无违规则填「无」）：**
- 条款编号 + 具体违规内容

**修改建议（若无则填「无」）：**
- 具体的修改方向和参考话术

**备注（可选，给运营人员看的补充说明）：**
- 其他值得注意的信息

---

请开始审核。"""

    def _get_image_media_type(self, file_path: Path) -> str:
        """根据文件扩展名获取 MIME 类型"""
        ext = file_path.suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        return media_types.get(ext, "image/jpeg")

    def review_image(self, file_path: Path, material_id: int, filename: str, uploader_email: str) -> ReviewResult:
        """对单份素材进行 AI 审核"""
        import requests

        logger.info(f"  正在审核：{filename}")

        try:
            # 读取图片并转为 base64
            image_data = base64.b64encode(file_path.read_bytes()).decode('utf-8')
            media_type = self._get_image_media_type(file_path)

            # 构建请求体
            payload = {
                "model": self.model,
                "max_tokens": 2048,
                "system": self.SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": self._build_user_prompt(filename),
                            },
                        ],
                    }
                ],
            }

            # 发送请求
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=self.headers,
                json=payload,
                timeout=240,
            )

            if response.status_code == 200:
                result_data = response.json()
                raw = result_data["content"][0]["text"]
                logger.info(f"  🤖 AI 回复已收到，长度：{len(raw)} 字符")
                logger.info(f"  🤖 AI 回复内容：{raw}")
       
            else:
                raise Exception(f"API 请求失败: {response.status_code} - {response.text}")

            # 解析结果
            return self._parse_response(material_id, filename, uploader_email, raw)

        except Exception as e:
            logger.error(f"  ⚠️  审核出错：{e}")
            return ReviewResult(
                material_id=material_id,
                filename=filename,
                uploader_email=uploader_email,
                status="needs_revision",
                violations=[f"AI 审核异常：{str(e)}"],
                suggestions=["请人工复审此素材"],
                notes=[],
                raw_response=str(e),
            )

    def _parse_response(
        self, material_id: int, filename: str, uploader_email: str, raw: str
    ) -> ReviewResult:
        """从回复中解析出结构化结果"""
        status = "pass"
        violations = []
        suggestions = []
        notes = []

        raw_lower = raw.lower()

        # 通过关键词判断审核结论
        if "❌" in raw or "违规" in raw or "拒绝" in raw_lower:
            status = "reject"
        elif "⚠️" in raw or "需修改" in raw or "修改" in raw_lower:
            status = "needs_revision"

        # 提取违规条款
        lines = raw.split("\n")
        in_violation = False
        in_suggestion = False
        for line in lines:
            stripped = line.strip()
            if "违规条款" in stripped or "违规内容" in stripped:
                in_violation = True
                in_suggestion = False
            elif "修改建议" in stripped or "建议" in stripped:
                in_suggestion = True
                in_violation = False
            elif in_violation and stripped.startswith("-"):
                violations.append(stripped.lstrip("-·*").strip())
            elif in_suggestion and stripped.startswith("-"):
                suggestions.append(stripped.lstrip("-·*").strip())

        return ReviewResult(
            material_id=material_id,
            filename=filename,
            uploader_email=uploader_email,
            status=status,
            violations=violations,
            suggestions=suggestions,
            notes=notes,
            raw_response=raw,
        )


class ReviewScheduler:
    """审核任务调度器"""

    def __init__(self):
        self.db = Database()
        self.storage = get_storage_instance()
        self.reviewer = AIReviewer()
        self.email_sender = EmailSender()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行中")
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info(f"✅ 审核调度器已启动，扫描间隔：{REVIEW_INTERVAL_MINUTES} 分钟")

    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("调度器已停止")

    def _run_loop(self):
        """调度器主循环"""
        while self._running:
            try:
                self.process_pending_materials()
            except Exception as e:
                logger.error(f"处理待审核素材时出错：{e}")

            # 每隔一定时间检查一次
            for _ in range(REVIEW_INTERVAL_MINUTES * 60):
                if not self._running:
                    break
                time.sleep(1)

    def process_pending_materials(self):
        """处理待审核的素材"""
        from config import UPLOADS_DIR

        # 获取待审核的素材
        pending_materials = self.db.get_pending_materials()
        
        if not pending_materials:
            return

        logger.info(f"📦 发现 {len(pending_materials)} 份待审核素材")

        for material in pending_materials:
            try:
                self._process_single_material(material)
            except Exception as e:
                logger.error(f"处理素材 {material['filename']} 时出错：{e}")

    def _process_single_material(self, material: dict):
        """处理单份素材"""
        material_id = material["id"]
        filename = material["filename"]
        file_path = Path(material["file_path"])
        uploader_email = material["uploader_email"]

        # 更新状态为审核中
        self.db.update_material_status(material_id, "reviewing")

        logger.info(f"  正在审核素材：{filename}")

        # 执行 AI 审核
        result = self.reviewer.review_image(
            file_path=file_path,
            material_id=material_id,
            filename=filename,
            uploader_email=uploader_email,
        )

        # 保存审核记录
        review_id = self.db.add_review(
            material_id=material_id,
            filename=filename,
            reviewer_result=result.status,
            violations=result.violations,
            suggestions=result.suggestions,
            notes=result.notes,
            raw_response=result.raw_response,
            reviewer_model=self.reviewer.model,
        )

        # 更新素材状态
        self.db.update_material_status(material_id, "reviewed")

        logger.info(f"  ✅ 审核完成：{filename} -> {result.status}")

        # 发送邮件通知
        self._send_notifications(material, result, review_id)

        # 保存审核报告
        self._save_report([result])

    def _send_notifications(self, material: dict, result: ReviewResult, review_id: int):
        """发送邮件通知"""
        from config import OPERATION_TEAM_EMAIL, UPLOADS_DIR

        # 发送邮件给达人（如果有邮箱）
        if result.uploader_email:
            try:
                # 构建用于邮件发送的结果格式
                review_results = [self._to_email_result(material, result)]
                self.email_sender.send_review_email(result.uploader_email, review_results)
                self.db.mark_review_email_sent(review_id)
                
                self.db.add_notification(
                    review_id=review_id,
                    material_id=material["id"],
                    recipient_email=result.uploader_email,
                    notification_type="creator",
                    status="success",
                )
                logger.info(f"  ✉️  已发送邮件通知达人：{result.uploader_email}")
            except Exception as e:
                logger.error(f"  ⚠️  发送邮件给达人失败：{e}")
                self.db.add_notification(
                    review_id=review_id,
                    material_id=material["id"],
                    recipient_email=result.uploader_email,
                    notification_type="creator",
                    status="failed",
                    error_message=str(e),
                )

        # 发送邮件给运营团队
        if OPERATION_TEAM_EMAIL:
            try:
                review_results = [self._to_email_result(material, result)]
                self.email_sender.send_review_email(OPERATION_TEAM_EMAIL, review_results)
                
                self.db.add_notification(
                    review_id=review_id,
                    material_id=material["id"],
                    recipient_email=OPERATION_TEAM_EMAIL,
                    notification_type="operation",
                    status="success",
                )
                logger.info(f"  ✉️  已发送邮件通知运营团队：{OPERATION_TEAM_EMAIL}")
            except Exception as e:
                logger.error(f"  ⚠️  发送邮件给运营团队失败：{e}")
                self.db.add_notification(
                    review_id=review_id,
                    material_id=material["id"],
                    recipient_email=OPERATION_TEAM_EMAIL,
                    notification_type="operation",
                    status="failed",
                    error_message=str(e),
                )

    def _to_email_result(self, material: dict, result: ReviewResult):
        """将审核结果转换为邮件发送所需的格式"""
        from email_sender import ReviewResult as Step1ReviewResult
        
        return Step1ReviewResult(
            filename=result.filename,
            email=result.uploader_email,
            file_path=material["file_path"],
            status=result.status,
            violations=result.violations,
            suggestions=result.suggestions,
            notes=result.notes,
            raw_response=result.raw_response,
        )

    def _save_report(self, results: List[ReviewResult]):
        """保存审核报告"""
        from config import REPORT_FORMAT
        import json

        REPORTS_DIR.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if REPORT_FORMAT == "json":
            report_path = REPORTS_DIR / f"review_report_{ts}.json"
            data = []
            for r in results:
                data.append({
                    "material_id": r.material_id,
                    "filename": r.filename,
                    "uploader_email": r.uploader_email,
                    "status": r.status,
                    "violations": r.violations,
                    "suggestions": r.suggestions,
                    "notes": r.notes,
                    "raw_response": r.raw_response,
                    "review_time": datetime.now().isoformat(),
                })
            report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            report_path = REPORTS_DIR / f"review_report_{ts}.md"
            report_path.write_text(self._build_markdown_report(results), encoding="utf-8")

        logger.info(f"📄 报告已保存：{report_path}")

    def _build_markdown_report(self, results: List[ReviewResult]) -> str:
        """生成 Markdown 格式的审核报告"""
        status_icon = {"pass": "✅", "needs_revision": "⚠️", "reject": "❌"}
        status_text = {
            "pass": "通过",
            "needs_revision": "需修改",
            "reject": "违规",
        }

        counts = {"pass": 0, "needs_revision": 0, "reject": 0}
        for r in results:
            counts[r.status] += 1

        lines = [
            f"# 素材审核报告",
            f"",
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"素材总数：{len(results)}",
            f"",
            f"## 审核摘要",
            f"",
            f"| 状态 | 数量 |",
            f"|------|------|",
        ]

        for s, label in status_text.items():
            icon = status_icon[s]
            lines.append(f"| {icon} {label} | {counts[s]} |")

        lines.extend(["", "---", ""])

        for r in results:
            lines.extend([
                f"### {r.filename}",
                f"",
                f"- **达人邮箱：** {r.uploader_email}",
                f"- **审核结果：** {status_icon[r.status]} {status_text[r.status]}",
                f"- **违规条款：** {', '.join(r.violations) if r.violations else '无'}",
                f"- **修改建议：** {', '.join(r.suggestions) if r.suggestions else '无'}",
                f"",
                f"## AI 审核详情",
                f"",
                f"```",
                r.raw_response,
                f"```",
                "",
                "---",
                "",
            ])

        return "\n".join(lines)

    def trigger_review(self, material_id: int):
        """手动触发单个素材的审核"""
        material = self.db.get_material(material_id)
        if not material:
            raise ValueError(f"素材不存在：{material_id}")
        
        self._process_single_material(material)

    def trigger_review_all(self):
        """手动触发所有待审核素材的审核"""
        self.process_pending_materials()
