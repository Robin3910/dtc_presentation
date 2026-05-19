"""
Markdown 解析器 - 将演讲文稿解析为结构化数据
"""
import re
from dataclasses import dataclass, field
from typing import Optional
from config import SOURCE_MD


@dataclass
class SlideContent:
    """单张幻灯片内容"""
    title: str           # 幻灯片标题
    label: str           # 顶部标签，如 "INTRO · 自我介绍"
    body: list[str]      # 正文段落列表
    bullets: list[str]   # 要点列表（从列表或表格提取）
    quote: Optional[str] = None   # 引言内容
    table_data: Optional[list[list[str]]] = None  # 表格数据


@dataclass
class Part:
    """一个 Part 的完整结构"""
    number: int          # Part 编号（1, 2, 3...）
    title: str           # 标题，如 "从对话到 AI 员工"
    slug: str            # URL 友好 slug
    hook: Optional[str] = None       # 开场金句
    slides: list[SlideContent] = field(default_factory=list)


class MarkdownParser:
    """
    解析演讲文稿 Markdown，提取 Part 结构与幻灯片内容。

    支持的 Markdown 特征：
    - ## Part N：标题（Part 分隔）
    - ### 小节标题（H3）
    - > 引用块（提取为金句）
    - | 表格（转为 HTML table）
    - - 列表（转为要点）
    - 普通段落
    """

    def __init__(self, md_path: str = None):
        self.md_path = md_path or SOURCE_MD
        self._content: str = ""

    # ------------------------------------------------------------------ 公开 API

    def parse(self) -> list[Part]:
        """解析完整 Markdown，返回 Part 列表"""
        self._content = self._read()
        parts_raw = self._split_parts()
        return [self._parse_part(block) for block in parts_raw if block.strip()]

    def get_file_hash(self) -> str:
        """返回文件的 MD5 哈希，用于变更检测"""
        import hashlib
        content = self._read()
        return hashlib.md5(content.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------ 内部方法

    def _read(self) -> str:
        with open(self.md_path, "r", encoding="utf-8") as f:
            return f.read()

    def _split_parts(self) -> list[str]:
        """按 ## Part N 分隔，返回各 Part 的原始文本块"""
        # 匹配 ## Part X 或 ## Part X： 标题
        pattern = r"(?=##\s+Part\s+\d+)"
        blocks = re.split(pattern, self._content)
        # 第一块是前言，合并到 Part 1
        if len(blocks) > 1 and not blocks[0].strip().startswith("## Part"):
            blocks[1] = blocks[0] + "\n" + blocks[1]
            blocks = blocks[1:]
        return blocks

    def _parse_part(self, text: str) -> Part:
        """将一个 Part 文本块解析为 Part 对象"""
        lines = text.strip().split("\n")
        header = lines[0] if lines else ""

        # 提取编号和标题
        num_match = re.search(r"Part\s+(\d+)", header)
        number = int(num_match.group(1)) if num_match else 1

        # 提取 Part 标题（## Part N：标题 或 ## Part N 标题）
        title_match = re.search(r"(?::|：)\s*(.+)$", header)
        title = title_match.group(1).strip() if title_match else header.replace("##", "").strip()

        # 生成 slug（只用标题部分，_to_slug 已清理前缀）
        slug = self._to_slug(title)

        # 提取开场金句（第一个 > 引用块）
        hook = None
        hook_match = re.search(r"^\s*>\s*(.+)$", text, re.MULTILINE)
        if hook_match:
            hook = hook_match.group(1).strip()

        # 提取所有小节
        sections = self._extract_sections(text)

        # 生成幻灯片
        slides = self._build_slides(number, title, sections, hook)

        return Part(number=number, title=title, slug=slug, hook=hook, slides=slides)

    def _extract_sections(self, text: str) -> list[dict]:
        """
        将 Part 文本拆分为多个小节，每个小节包含：
        - h3_title: H3 标题
        - paragraphs: 段落列表
        - bullets: 列表项
        - quote: 引言（如果有）
        - table: 表格数据（如果有）
        """
        sections = []
        current = {"h3_title": "开场", "paragraphs": [], "bullets": [], "quote": None, "table": None}

        lines = text.split("\n")
        in_table = False
        table_rows = []

        for line in lines:
            stripped = line.strip()

            # H3 分隔新小节
            if stripped.startswith("### "):
                if current["paragraphs"] or current["bullets"] or current["quote"]:
                    sections.append(current)
                current = {"h3_title": stripped[4:].strip(), "paragraphs": [], "bullets": [], "quote": None, "table": None}
                in_table = False
                continue

            # 跳过 Part 标题行、水平线和空行
            if stripped.startswith("##") or stripped.startswith("---") or stripped == "":
                in_table = False
                continue

            # 表格处理
            if "|" in stripped and stripped.lstrip().startswith("|"):
                if not in_table:
                    in_table = True
                    table_rows = []
                # 解析表格行（排除对齐行 |---|）
                if not re.match(r"^\|[\s\-:|]+\|$", stripped):
                    cells = [c.strip() for c in stripped.split("|")[1:-1]]
                    table_rows.append(cells)
                continue
            else:
                if in_table and table_rows:
                    current["table"] = table_rows
                    table_rows = []
                in_table = False

            # 引言
            if stripped.startswith(">"):
                current["quote"] = stripped[1:].strip()
                continue

            # 列表项
            if stripped.startswith("- ") or stripped.startswith("* "):
                current["bullets"].append(stripped[2:].strip())
                continue

            # 普通段落（去除 Markdown 语法）
            if stripped:
                # 去除 **bold** 保留文字
                clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
                current["paragraphs"].append(clean)

        if current["paragraphs"] or current["bullets"] or current["quote"] or current["table"]:
            if in_table and table_rows:
                current["table"] = table_rows
            sections.append(current)

        return sections

    def _build_slides(self, part_num: int, part_title: str, sections: list[dict], hook: str = None) -> list[SlideContent]:
        """将小节列表转换为幻灯片内容列表"""
        slides = []

        # 第1张：Part 封面（金句页）
        if hook:
            slides.append(SlideContent(
                title=f"Part {part_num}",
                label=f"PART {part_num} · 开场",
                body=[hook],
                bullets=[],
            ))

        for sec in sections:
            # 跳过仅有占位符的小节（如 "(待补充)"）
            content_text = " ".join(sec["paragraphs"])
            if "(待补充)" in content_text and not sec["bullets"]:
                continue

            bullets = sec["bullets"]
            paragraphs = sec["paragraphs"]

            # 如果有小节标题，生成标题页
            if sec["h3_title"] and sec["h3_title"] not in ("开场",):
                slides.append(SlideContent(
                    title=sec["h3_title"],
                    label=self._section_label(part_num, sec["h3_title"]),
                    body=[],
                    bullets=[],
                ))

            # 如果有表格
            if sec["table"]:
                slides.append(SlideContent(
                    title="数据对比",
                    label=self._section_label(part_num, "对比"),
                    body=paragraphs[:1] if paragraphs else [],
                    bullets=[],
                    table_data=sec["table"],
                ))
                paragraphs = paragraphs[1:] if paragraphs else []

            # 如果有引言
            if sec["quote"] and not hook:
                slides.append(SlideContent(
                    title="",
                    label="",
                    body=[sec["quote"]],
                    bullets=[],
                    quote=sec["quote"],
                ))

            # 如果有列表
            if bullets:
                # 超过 4 条的列表单独成页
                if len(bullets) > 4:
                    mid = len(bullets) // 2
                    slides.append(SlideContent(
                        title="要点",
                        label=self._section_label(part_num, sec["h3_title"]),
                        body=paragraphs,
                        bullets=bullets[:mid],
                    ))
                    slides.append(SlideContent(
                        title="要点（续）",
                        label=self._section_label(part_num, sec["h3_title"]),
                        body=[],
                        bullets=bullets[mid:],
                    ))
                else:
                    slides.append(SlideContent(
                        title="要点",
                        label=self._section_label(part_num, sec["h3_title"]),
                        body=paragraphs,
                        bullets=bullets,
                    ))
                paragraphs = []

            # 剩余段落
            for para in paragraphs:
                slides.append(SlideContent(
                    title="",
                    label="",
                    body=[para],
                    bullets=[],
                ))

        return slides

    def _section_label(self, part_num: int, title: str) -> str:
        """生成规范化的标签，如 INTRO · 自我介绍"""
        keywords = {
            "自我介绍": "INTRO",
            "初遇": "STORY",
            "原理": "CORE",
            "本质": "CORE",
            "工具": "LANDSCAPE",
            "工作面板": "WORKFLOW",
            "门槛": "PROBLEM",
            "心法": "INSIGHT",
            "效果": "VISION",
            "愿景": "VISION",
            "原则": "PRINCIPLE",
            "Skills": "SKILLS",
            "感悟": "PHILOSOPHY",
            "行业": "TREND",
            "Git": "TOOLS",
            "Token": "COST",
            "团队": "TEAM",
            "案例": "CASE",
            "Demo": "DEMO",
            "组建": "SETUP",
            "待补充": "",
        }
        for kw, label in keywords.items():
            if kw in title:
                return f"PART {part_num} · {label}" if label else f"PART {part_num}"
        return f"PART {part_num} · {title[:6]}"

    @staticmethod
    def _to_slug(text: str) -> str:
        """文本转 URL 友好 slug"""
        import re
        # 先去除 ## Part N 编号前缀和冒号
        slug = re.sub(r"##\s*Part\s*\d+[:：]\s*", "", text)
        # 去除所有特殊字符，只保留中文、字母、数字、空格、横线
        slug = re.sub(r"[^\w\s\u4e00-\u9fff-]", "", slug)
        # 空格和横线统一转为单横线
        slug = re.sub(r"[-_\s]+", "-", slug).strip("-")
        return slug.lower()
