# -*- coding: utf-8 -*-
"""
AI 审核客户端：用于达人素材图片的内容审核

使用 DMXAPI 中转站调用 Claude 模型进行图片分析。
DMXAPI 文档：https://doc.dmxapi.cn/claude-image.html

优势：
- 支持 OpenAI 兼容格式
- 价格优惠
- 稳定可靠
"""

import base64
import json
import time
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Literal

from config import (
    DMXAPI_API_KEY,
    DMXAPI_BASE_URL,
    CLAUDE_MODEL,
    BRAND_RULES_FILE,
    REPORTS_DIR,
    REPORT_FORMAT,
)


@dataclass
class ReviewResult:
    """单份素材的审核结果"""
    filename: str
    email: str
    file_path: str
    status: Literal["pass", "needs_revision", "reject"] = "pass"
    violations: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    raw_response: str = ""


class ClaudeReviewer:
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
        # DMXAPI 服务地址（完整 URL）
        self.base_url = DMXAPI_BASE_URL.rstrip("/")  # 移除末尾斜杠
        self.model = CLAUDE_MODEL
        print(f"✅ 使用 DMXAPI + Claude 模型：{self.model}")
        print(f"✅ API 地址：{self.base_url}")

        self.rules_text = BRAND_RULES_FILE.read_text(encoding="utf-8")
        self.reports_dir = REPORTS_DIR
        self.reports_dir.mkdir(exist_ok=True)

        # 请求头配置（与官方示例一致）
        self.headers = {
            "content-type": "application/json",  # 小写，与官方示例一致
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

    def _extract_email_from_filename(self, filename: str) -> str:
        """从文件名中提取邮箱地址作为达人联系方式"""
        # 文件名格式示例：user001@foxmail.com.png
        name_without_ext = Path(filename).stem
        if "@" in name_without_ext and "." in name_without_ext:
            return name_without_ext
        return ""

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

    def review_single(self, file_path: Path) -> ReviewResult:
        """对单份素材进行 AI 审核（使用 DMXAPI 中转站）"""
        filename = file_path.name
        email = self._extract_email_from_filename(filename)

        print(f"  正在审核：{filename} → {email or '未找到邮箱'}")

        try:
            # 读取图片并转为 base64
            image_data = base64.b64encode(file_path.read_bytes()).decode('utf-8')
            media_type = self._get_image_media_type(file_path)

            # 构建请求体（Anthropic Messages API 格式）
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

            # 发送请求到 DMXAPI（官方示例格式）
            response = requests.post(
                f"{self.base_url}/v1/messages",
                headers=self.headers,
                json=payload,
                timeout=240,  # 120秒超时，防止大图片分析时超时
            )

            # 处理响应
            if response.status_code == 200:
                result_data = response.json()
                # DMXAPI 返回格式兼容 OpenAI/Anthropic
                raw = result_data["content"][0]["text"]
                # 打印模型回复内容到控制台
                print(f"\n  🤖 模型回复：")
                print("  " + "-" * 46)
                for line in raw.split('\n'):
                    print(f"  {line}")
                print("  " + "-" * 46 + "\n")
            else:
                raise Exception(f"API 请求失败: {response.status_code} - {response.text}")

            return self._parse_response(filename, email, str(file_path), raw)

        except Exception as e:
            print(f"  ⚠️  审核出错：{e}")
            result = ReviewResult(
                filename=filename,
                email=email,
                file_path=str(file_path),
                status="needs_revision",
                violations=[f"AI 审核异常：{str(e)}"],
                suggestions=["请人工复审此素材"],
            )
            result.raw_response = str(e)
            return result

    def _parse_response(
        self, filename: str, email: str, file_path: str, raw: str
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

        # 提取违规条款（粗略匹配）
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

        result = ReviewResult(
            filename=filename,
            email=email,
            file_path=file_path,
            status=status,
            violations=violations,
            suggestions=suggestions,
            notes=notes,
            raw_response=raw,
        )
        return result

    def review_all(self, materials_dir: Path) -> list[ReviewResult]:
        """对素材目录中的所有图片进行批量审核"""
        supported_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        files = sorted(
            f for f in materials_dir.iterdir()
            if f.is_file() and f.suffix.lower() in supported_exts
        )

        if not files:
            print(f"⚠️  未在 {materials_dir} 中找到任何图片文件")
            return []

        print(f"\n📦 发现 {len(files)} 份待审核素材：")
        for f in files:
            print(f"   - {f.name}")
        print()

        results = []
        for i, file_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}]", end=" ")
            result = self.review_single(file_path)
            results.append(result)
            if i < len(files):
                time.sleep(1)  # 避免 API 限速

        return results

    def save_report(self, results: list[ReviewResult], report_name: str = "") -> Path:
        """将审核结果保存为报告文件"""
        if not report_name:
            from datetime import datetime
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"review_report_{ts}"

        if REPORT_FORMAT == "json":
            report_path = self.reports_dir / f"{report_name}.json"
            data = []
            for r in results:
                data.append({
                    "filename": r.filename,
                    "email": r.email,
                    "file_path": r.file_path,
                    "status": r.status,
                    "violations": r.violations,
                    "suggestions": r.suggestions,
                    "notes": r.notes,
                    "raw_response": r.raw_response,
                })
            report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            report_path = self.reports_dir / f"{report_name}.md"
            report_path.write_text(self._build_markdown_report(results), encoding="utf-8")

        print(f"\n📄 报告已保存：{report_path}")
        return report_path

    def _build_markdown_report(self, results: list[ReviewResult]) -> str:
        """生成 Markdown 格式的审核报告"""
        from datetime import datetime

        status_icon = {"pass": "✅", "needs_revision": "⚠️", "reject": "❌"}
        status_text = {
            "pass": "通过",
            "needs_revision": "需修改",
            "reject": "违规",
        }

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

        counts = {"pass": 0, "needs_revision": 0, "reject": 0}
        for r in results:
            counts[r.status] += 1

        for s, label in status_text.items():
            icon = status_icon[s]
            lines.append(f"| {icon} {label} | {counts[s]} |")

        lines.extend(["", "---", ""])

        for r in results:
            lines.extend([
                f"### {r.filename}",
                f"",
                f"- **达人邮箱：** {r.email}",
                f"- **审核结果：** {status_icon[r.status]} {status_text[r.status]}",
                f"- **违规条款：** {', '.join(r.violations) if r.violations else '无'}",
                f"- **修改建议：** {', '.join(r.suggestions) if r.suggestions else '无'}",
                f"- **备注：** {', '.join(r.notes) if r.notes else '无'}",
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
