"""
HTML 生成器 - 根据 Part 数据生成完整的 HTML 幻灯片
"""
import datetime
from config import OUTPUT_FILENAME_TEMPLATE
from md_parser import Part, SlideContent, MarkdownParser


class HTMLGenerator:
    """
    将 Part 数据渲染为 HTML 幻灯片。

    设计规范（与 web页面生成/.claude/claude.md 保持一致）：
    - 风格：苹果科技简约风，黑白配色
    - 字体：SF Pro Display / SF Pro Text / SF Mono
    - 背景：深色 (#000) / 浅色 (#fff) / 渐变
    - 动画：fadeUp 入场动画，6 层延迟
    - 布局：16:9 比例锁定，支持键盘/触摸导航
    """

    def __init__(self):
        self._all_parts_: list = []

    # ------------------------------------------------------------------------- 静态模板（CSS + JS）

    _HTML_HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --black: #000000;
            --white: #ffffff;
            --gray-100: #f5f5f7;
            --gray-200: #e8e8ed;
            --gray-300: #d2d2d7;
            --gray-400: #86868b;
            --gray-500: #6e6e73;
            --gray-600: #424245;
            --gray-700: #2d2d30;
            --gray-800: #1d1d1f;
            --gray-900: #0a0a0a;
            --font-h: 'SF Pro Display', -apple-system, 'Segoe UI', Arial, sans-serif;
            --font-b: 'SF Pro Text', -apple-system, 'Segoe UI', Arial, sans-serif;
            --font-m: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: var(--black); color: var(--white); font-family: var(--font-b); overflow: hidden; -webkit-font-smoothing: antialiased; }}

        .deck {{ position: relative; width: 100vw; height: 100vh; overflow: hidden; }}
        @media (min-width: 769px) {{
            .deck {{ max-width: calc(100vh * 16 / 9); max-height: calc(100vw * 9 / 16); margin: auto; position: absolute; inset: 0; }}
        }}

        .slide {{ position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 80px 10%; opacity: 0; visibility: hidden; transition: opacity 0.5s; overflow: hidden; }}
        .slide.active {{ opacity: 1; visibility: visible; }}
        .slide.light {{ background: var(--white); color: var(--black); }}
        .slide.gray-g {{ background: radial-gradient(ellipse at 30% 50%, #1a1a2e 0%, #0a0a0a 60%, #000 100%); }}
        .slide.deep-g {{ background: radial-gradient(ellipse at 70% 30%, #0f0f18 0%, #060610 50%, #000 100%); }}
        .slide.warm-light {{ background: linear-gradient(160deg, #f8f8f6 0%, #f0f0ee 100%); }}

        .content {{ width: 100%; max-height: 100%; overflow: hidden; display: flex; flex-direction: column; justify-content: center; gap: 20px; }}
        .content.centered {{ align-items: center; text-align: center; }}
        .scroll {{ overflow-y: auto; max-height: 100%; width: 100%; scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.08) transparent; }}
        .scroll::-webkit-scrollbar {{ width: 3px; }}
        .scroll::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,.08); border-radius: 2px; }}

        h1 {{ font-family: var(--font-h); font-size: clamp(34px,6.5vw,84px); font-weight: 700; letter-spacing: -.03em; line-height: 1.05; }}
        h2 {{ font-family: var(--font-h); font-size: clamp(24px,4vw,54px); font-weight: 700; letter-spacing: -.025em; line-height: 1.1; }}
        h3 {{ font-family: var(--font-h); font-size: clamp(15px,2vw,26px); font-weight: 600; letter-spacing: -.015em; }}
        p, li {{ font-family: var(--font-b); font-size: clamp(13px,1.6vw,20px); line-height: 1.65; color: var(--gray-400); }}
        .light p, .light li {{ color: var(--gray-600); }}
        .sub {{ font-size: clamp(14px,2vw,24px); color: var(--gray-400); }}
        .label {{ font-family: var(--font-m); font-size: clamp(10px,1vw,13px); font-weight: 500; letter-spacing: .15em; text-transform: uppercase; color: var(--gray-500); }}
        .light .label {{ color: var(--gray-400); }}

        .gt {{ background: linear-gradient(135deg,#fff 0%,#a0a0a0 50%,#fff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }}
        .dot-grid {{ position: absolute; inset: 0; background-image: radial-gradient(circle,rgba(255,255,255,.055) 1px,transparent 1px); background-size: 32px 32px; pointer-events: none; }}
        .light .dot-grid {{ background-image: radial-gradient(circle,rgba(0,0,0,.055) 1px,transparent 1px); }}
        .la {{ width: 48px; height: 2px; background: var(--gray-600); }}
        .la.w {{ background: rgba(255,255,255,.25); }}

        .stat-row {{ display: flex; gap: clamp(32px,5vw,56px); flex-wrap: wrap; }}
        .stat-block {{ display: flex; flex-direction: column; gap: 4px; }}
        .sn {{ font-family: var(--font-h); font-size: clamp(40px,6vw,72px); font-weight: 700; letter-spacing: -.04em; line-height: 1; }}
        .sl {{ font-size: clamp(11px,1.2vw,15px); color: var(--gray-500); }}
        .light .sl {{ color: var(--gray-400); }}

        .card-g {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 14px; width: 100%; }}
        .card {{ background: rgba(255,255,255,.03); border: 1px solid rgba(255,255,255,.06); border-radius: 16px; padding: 22px 20px; display: flex; flex-direction: column; gap: 8px; transition: background .25s, border-color .25s; }}
        .card:hover {{ background: rgba(255,255,255,.05); border-color: rgba(255,255,255,.1); }}
        .light .card {{ background: rgba(0,0,0,.03); border-color: rgba(0,0,0,.07); }}
        .light .card:hover {{ background: rgba(0,0,0,.055); border-color: rgba(0,0,0,.12); }}
        .card h3 {{ font-size: clamp(13px,1.4vw,17px); color: var(--white); font-weight: 600; }}
        .light .card h3 {{ color: var(--black); }}
        .card p {{ font-size: clamp(11px,1.15vw,14px); color: var(--gray-500); line-height: 1.5; }}
        .card-num {{ font-family: var(--font-m); font-size: 18px; font-weight: 700; color: var(--white); opacity: .2; }}

        .hl-box {{ background: rgba(255,255,255,.03); border-left: 2px solid var(--gray-600); border-radius: 0 8px 8px 0; padding: 14px 20px; width: 100%; }}
        .hl-box p {{ font-size: clamp(12px,1.4vw,17px); color: var(--gray-200); line-height: 1.6; }}
        .light .hl-box {{ background: rgba(0,0,0,.03); border-left-color: var(--gray-400); }}
        .light .hl-box p {{ color: var(--gray-700); }}

        .quote {{ border-left: 2px solid var(--gray-700); padding-left: 20px; width: 100%; }}
        .quote blockquote {{ font-family: var(--font-h); font-size: clamp(15px,2vw,26px); font-weight: 500; line-height: 1.45; color: var(--gray-200); letter-spacing: -.01em; }}
        .quote cite {{ display: block; margin-top: 10px; font-size: clamp(10px,1.1vw,13px); color: var(--gray-500); font-style: normal; font-family: var(--font-m); }}
        .light .quote {{ border-left-color: var(--gray-400); }}
        .light .quote blockquote {{ color: var(--gray-700); }}

        .bul {{ list-style: none; display: flex; flex-direction: column; gap: 10px; }}
        .bul li {{ display: flex; align-items: flex-start; gap: 12px; font-size: clamp(13px,1.4vw,17px); color: var(--gray-300); }}
        .bul li::before {{ content: '—'; color: var(--gray-600); flex-shrink: 0; margin-top: 2px; font-family: var(--font-m); }}
        .light .bul li {{ color: var(--gray-700); }}

        .tag {{ display: inline-block; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09); border-radius: 20px; padding: 5px 14px; font-size: clamp(11px,1.1vw,13px); color: var(--gray-400); }}
        .tag-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}

        .flow-r {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
        .flow-n {{ background: rgba(255,255,255,.04); border: 1px solid rgba(255,255,255,.09); border-radius: 10px; padding: 10px 18px; font-family: var(--font-m); font-size: clamp(10px,1.2vw,14px); color: var(--gray-300); white-space: nowrap; }}
        .flow-n.hl {{ background: rgba(255,255,255,.09); border-color: rgba(255,255,255,.18); color: var(--white); font-weight: 600; }}
        .flow-n.dk {{ background: rgba(0,0,0,.06); border-color: rgba(0,0,0,.12); color: var(--gray-700); }}
        .flow-n.dk.hl {{ background: rgba(0,0,0,.1); border-color: rgba(0,0,0,.18); color: var(--black); font-weight: 700; }}
        .flow-ar {{ color: var(--gray-600); font-size: clamp(14px,1.4vw,20px); flex-shrink: 0; }}
        .flow-ar.dk {{ color: var(--gray-400); }}

        .split {{ display: flex; gap: 32px; width: 100%; align-items: flex-start; }}
        .split-main {{ flex: 1; min-width: 0; }}
        .split-aside {{ flex: 0 0 auto; max-width: 260px; }}

        .tbl {{ width: 100%; border-collapse: collapse; font-size: clamp(10px,1.1vw,13px); }}
        .tbl th {{ text-align: left; padding: 10px 14px; font-weight: 600; color: var(--gray-400); border-bottom: 1px solid rgba(255,255,255,.08); font-size: clamp(9px,1vw,12px); letter-spacing: .05em; text-transform: uppercase; white-space: nowrap; }}
        .tbl td {{ padding: 10px 14px; color: var(--gray-300); border-bottom: 1px solid rgba(255,255,255,.04); vertical-align: top; line-height: 1.45; }}
        .tbl tr:last-child td {{ border-bottom: none; }}
        .tbl td:first-child {{ color: var(--white); font-weight: 500; }}
        .light .tbl th {{ color: var(--gray-400); border-bottom-color: rgba(0,0,0,.08); }}
        .light .tbl td {{ color: var(--gray-600); border-bottom-color: rgba(0,0,0,.04); }}
        .light .tbl td:first-child {{ color: var(--black); }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: clamp(9px,.9vw,11px); font-weight: 600; }}
        .badge-free {{ background: rgba(80,200,120,.15); color: #50c878; }}
        .badge-paid {{ background: rgba(255,180,80,.15); color: #ffb450; }}

        .progress {{ position: fixed; top: 0; left: 0; height: 2px; background: linear-gradient(90deg,#fff,#888); transition: width .4s; z-index: 1000; }}
        .nav {{ position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 20px; z-index: 1000; }}
        .nav-btn {{ background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); color: var(--white); width: 40px; height: 40px; border-radius: 50%; cursor: pointer; font-size: 16px; display: flex; align-items: center; justify-content: center; transition: background .2s, transform .15s; font-family: var(--font-b); user-select: none; }}
        .nav-btn:hover {{ background: rgba(255,255,255,.12); transform: scale(1.05); }}
        .nav-btn:active {{ transform: scale(.95); }}
        .counter {{ color: rgba(255,255,255,.35); font-size: 13px; font-family: var(--font-m); letter-spacing: .05em; min-width: 50px; text-align: center; }}
        .snum {{ position: absolute; top: 32px; right: 40px; font-family: var(--font-m); font-size: 12px; color: rgba(255,255,255,.2); letter-spacing: .1em; }}
        .light .snum {{ color: rgba(0,0,0,.2); }}

        @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(24px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .ai {{ animation: fadeUp .6s cubic-bezier(.25,.1,.25,1) forwards; opacity: 0; }}
        .ai1 {{ animation-delay: .08s; }}
        .ai2 {{ animation-delay: .18s; }}
        .ai3 {{ animation-delay: .30s; }}
        .ai4 {{ animation-delay: .44s; }}
        .ai5 {{ animation-delay: .58s; }}
        .ai6 {{ animation-delay: .72s; }}

        @media (max-width: 768px) {{ .slide {{ padding: 48px 6% 80px; justify-content: flex-start; }} h1 {{ font-size: clamp(30px,8vw,48px); }} h2 {{ font-size: clamp(20px,5vw,34px); }} .card-g {{ grid-template-columns: 1fr; gap: 12px; }} .stat-row {{ gap: 24px; }} .split {{ flex-direction: column; gap: 20px; }} .split-aside {{ max-width: 100%; }} .snum {{ top: 20px; right: 20px; }} .nav {{ bottom: 20px; gap: 14px; }} .nav-btn {{ width: 36px; height: 36px; font-size: 14px; }} }}
        @media (max-width: 480px) {{ .slide {{ padding: 40px 5% 72px; }} .stat-row {{ flex-direction: column; gap: 16px; }} }}
    </style>
</head>
<body>
"""

    _HTML_FOOT = """
<script>
    const slides = document.querySelectorAll('.slide');
    const total = slides.length;
    let cur = 1;
    document.getElementById('total').textContent = total;

    function show(n) {{
        if (n < 1) n = 1;
        if (n > total) n = total;
        cur = n;
        slides.forEach((s, i) => s.classList.toggle('active', i === n - 1));
        document.getElementById('cur').textContent = n;
        document.getElementById('bar').style.width = (n / total * 100) + '%';
        slides[n - 1].querySelectorAll('.ai').forEach(el => {{
            el.style.animation = 'none';
            el.offsetHeight;
            el.style.animation = null;
        }});
    }}

    function next() {{ show(cur + 1); }}
    function prev() {{ show(cur - 1); }}

    document.addEventListener('keydown', e => {{
        if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {{ e.preventDefault(); next(); }}
        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{ e.preventDefault(); prev(); }}
    }});
    document.addEventListener('click', e => {{ if (!e.target.closest('.nav')) next(); }});
    let tx = 0;
    document.addEventListener('touchstart', e => {{ tx = e.touches[0].clientX; }});
    document.addEventListener('touchend', e => {{ const d = tx - e.changedTouches[0].clientX; if (Math.abs(d) > 50) d > 0 ? next() : prev(); }});
    show(1);
</script>
</body>
</html>
"""

    # ------------------------------------------------------------------------- 渲染方法

    def generate(self, parts: list[Part], timestamp: str) -> dict[str, str]:
        """
        将 Part 列表渲染为 HTML 文件内容。
        返回 {filename: html_content} 字典。
        """
        # 收集所有幻灯片（包含 part 归属信息）
        all_slides: list[tuple[Part, SlideContent, int]] = []  # (part, slide, global_index)
        for part in parts:
            for slide in part.slides:
                all_slides.append((part, slide, len(all_slides) + 1))

        total = len(all_slides)
        if total == 0:
            return {}

        # 按 Part 分组渲染
        part_blocks: dict[int, str] = {}
        for part in parts:
            part_blocks[part.number] = self._render_part_group(part, all_slides, total)

        # 组装完整 HTML
        full_title = " / ".join([f"Part {p.number}: {p.title}" for p in parts])
        html = self._HTML_HEAD.format(title=full_title)
        html += '<div class="progress" id="bar"></div>\n<div class="deck">\n'

        for part in parts:
            html += part_blocks[part.number]

        html += '</div>\n'
        html += '<div class="nav">\n'
        html += f'  <button class="nav-btn" onclick="prev()" aria-label="上一页">&#8592;</button>\n'
        html += f'  <span class="counter"><span id="cur">1</span> / <span id="total">{total}</span></span>\n'
        html += f'  <button class="nav-btn" onclick="next()" aria-label="下一页">&#8594;</button>\n'
        html += '</div>\n'
        html += self._HTML_FOOT.format()

        # 按 Part 生成独立文件 + 合并版
        result = {}
        for part in parts:
            slug = f"part{part.number}-{part.slug}"
            fname = OUTPUT_FILENAME_TEMPLATE.format(part_slug=slug, timestamp=timestamp)
            result[fname] = self._render_part_standalone(part, timestamp, total)

        # 合并版（生成一次，不要在循环内）
        result["all_parts_" + timestamp + ".html"] = html

        return result

    def _render_part_group(self, part: Part, all_slides: list, total: int) -> str:
        """渲染一个 Part 的所有幻灯片（作为完整 HTML 的一部分）"""
        blocks = []
        for idx, (p, slide, gidx) in enumerate(all_slides):
            if p.number != part.number:
                continue
            blocks.append(self._render_slide(slide, gidx, total, is_first=(gidx == 1)))
        return "\n".join(blocks)

    def _render_part_standalone(self, part: Part, timestamp: str, total_in_all: int) -> str:
        """渲染单个 Part 的独立 HTML 文件"""
        slides_html = []
        global_start = 1
        for p in [p for p in self._all_parts_ if p.number < part.number]:
            global_start += len(p.slides)

        for idx, slide in enumerate(part.slides, global_start):
            slides_html.append(self._render_slide(slide, idx, total_in_all, is_first=(idx == 1)))

        html = self._HTML_HEAD.format(title=f"Part {part.number}: {part.title}")
        html += '<div class="progress" id="bar"></div>\n<div class="deck">\n'
        html += "\n".join(slides_html)
        html += '</div>\n'
        html += '<div class="nav">\n'
        html += f'  <button class="nav-btn" onclick="prev()" aria-label="上一页">&#8592;</button>\n'
        html += f'  <span class="counter"><span id="cur">1</span> / <span id="total">{total_in_all}</span></span>\n'
        html += f'  <button class="nav-btn" onclick="next()" aria-label="下一页">&#8594;</button>\n'
        html += '</div>\n'
        html += self._HTML_FOOT.format()
        return html

    def set_all_parts(self, parts: list[Part]):
        """注入所有 Part，用于 standalone 文件的 global_start 计算"""
        self._all_parts_ = parts

    def _render_slide(self, slide: SlideContent, index: int, total: int, is_first: bool = False) -> str:
        """将单张幻灯片数据渲染为 HTML 片段"""
        label_html = f'<div class="label ai ai1">{slide.label}</div>' if slide.label else ""
        title_html = f'<h2 class="ai ai2" style="max-width:20ch;margin-top:4px;">{slide.title}</h2>' if slide.title else ""

        # 确定背景风格
        if is_first:
            bg_cls = "gray-g"
        elif index % 5 == 0:
            bg_cls = "deep-g"
        elif index % 4 == 3:
            bg_cls = "light warm-light"
        elif index % 4 == 2:
            bg_cls = "light"
        else:
            bg_cls = ""

        body_parts = []

        # 引言/金句处理
        if slide.quote and not slide.body:
            body_parts.append(f'''
            <div class="quote ai ai2">
                <blockquote>"{slide.quote}"</blockquote>
            </div>''')

        # 段落
        for para in slide.body:
            body_parts.append(f'<p class="ai ai3">{para}</p>')

        # 表格
        if slide.table_data:
            body_parts.append(self._render_table(slide.table_data))

        # 列表
        if slide.bullets:
            li_items = "\n".join([f'<li>{b}</li>' for b in slide.bullets])
            body_parts.append(f'<ul class="bul ai ai4">{li_items}</ul>')

        body_html = "\n".join(body_parts)

        return f'''
    <div class="slide {bg_cls}" id="slide-{index}">
        <div class="dot-grid"></div>
        <div class="snum">{index} / {total}</div>
        <div class="content{' centered' if is_first else ''}">
            {label_html}
            {title_html}
            <div class="la{' w' if bg_cls in ('', 'gray-g', 'deep-g') else ''} ai ai2"></div>
            {body_html}
        </div>
    </div>'''

    def _render_table(self, table_data: list[list[str]]) -> str:
        """渲染 Markdown 表格为 HTML"""
        if not table_data or len(table_data) < 2:
            return ""
        headers = table_data[0]
        rows = table_data[1:]
        th_html = "".join([f"<th>{h}</th>" for h in headers])
        tr_html = ""
        for row in rows:
            td_html = "".join([f"<td>{c}</td>" for c in row])
            tr_html += f"<tr>{td_html}</tr>"
        return f'<table class="tbl ai ai3"><thead><tr>{th_html}</tr></thead><tbody>{tr_html}</tbody></table>'
