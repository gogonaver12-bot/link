"""PPT 자동 생성: 간단한 글(개요) → 16:9 발표자료. AI 체크 시 주제만으로 내용 작성."""
from datetime import date
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

from office_suite.core import Field, Result

KEY = "ppt"
NAME = "📊 PPT 자동 만들기"
DESC = "'# 제목' 줄 = 새 슬라이드, '- ' = 항목, '| 가 | 나 |' = 표, '그림: 파일경로' = 사진"
ORDER = 10
FONT = "맑은 고딕"
THEMES = {"파랑": ("1F4E79", "2E75B6"), "초록": ("375623", "70AD47"),
          "주황": ("843C0C", "ED7D31"), "회색": ("262626", "7F7F7F")}
SAMPLE = """# 공사 개요
- 현장: ○○공장 수배전반 교체
- 기간: 2주 (야간 작업 포함)
  - 정전 작업은 주말 진행
# 주요 작업
| 구분 | 내용 | 수량 |
| 수배전반 | 저압반 교체 | 2면 |
| PLC | 제어반 프로그램 수정 | 1식 |
# 일정 및 안전
- 1주차: 자재 반입, 배관·배선
- 2주차: 결선, 시운전, 준공 검사
- 작업 전 정전 확인 및 잠금 표지(LOTO)"""

FIELDS = [
    Field("title", "발표 제목", "text", "공사 계획 보고"),
    Field("subtitle", "부제 (비우면 회사명·날짜)", "text", ""),
    Field("outline", "내용 (개요)", "multiline", SAMPLE),
    Field("txt", "또는 내용 파일 (.txt)", "file", ""),
    Field("theme", "색상", "choice", "파랑", choices=tuple(THEMES)),
    Field("use_ai", "AI가 내용 써주기 (주제만 쓰면 됨, AI 키 필요)", "check", False),
    Field("n", "AI 사용 시 슬라이드 수", "number", 6),
]


def parse(text):
    slides, cur = [], None
    for line in text.splitlines():
        st = line.strip()
        if not st or st.startswith("```"):
            continue
        if st.startswith("#"):
            cur = {"title": st.lstrip("#").strip(), "bullets": [], "table": [], "images": []}
            slides.append(cur)
            continue
        if cur is None:
            cur = {"title": "", "bullets": [], "table": [], "images": []}
            slides.append(cur)
        if st.startswith("|"):
            cells = [c.strip() for c in st.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):   # 마크다운 구분줄(|---|) 무시
                cur["table"].append(cells)
        elif st.lower().startswith(("그림:", "사진:", "img:", "image:")):
            cur["images"].append(st.split(":", 1)[1].strip().strip('"'))
        else:
            level = 1 if line[:1] in (" ", "\t") or st.startswith("--") else 0
            cur["bullets"].append((level, st.lstrip("-*•·").strip()))
    return slides


def _text(slide, txt, x, y, w, h, size, color, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap, tf.vertical_anchor = True, anchor
    lines = txt if isinstance(txt, list) else [(0, txt)]
    for i, (lvl, t) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = (("      – " if lvl else "• ") + t) if isinstance(txt, list) else t
        f = r.font
        f.name, f.size, f.bold, f.color.rgb = FONT, Pt(size - 3 * lvl), bold, color
        if isinstance(txt, list):
            p.space_after = Pt(8)
    return tb


def _rect(slide, x, y, w, h, color):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = color
    s.line.fill.background()
    return s


def _table(slide, rows, x, y, w, h, dark):
    ncol = max(len(r) for r in rows)
    shp = slide.shapes.add_table(len(rows), ncol, Inches(x), Inches(y), Inches(w), Inches(h))
    size = 16 if len(rows) <= 6 else 12
    for i, row in enumerate(rows):
        for j in range(ncol):
            cell = shp.table.cell(i, j)
            cell.text = row[j] if j < len(row) else ""
            for p in cell.text_frame.paragraphs:
                for r in p.runs:
                    r.font.name, r.font.size, r.font.bold = FONT, Pt(size), i == 0
                    if i == 0:
                        r.font.color.rgb = RGBColor(255, 255, 255)
            if i == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = dark


def build(title, subtitle, slides, theme, path, footer=""):
    dark, accent = (RGBColor.from_string(c) for c in THEMES.get(theme, THEMES["파랑"]))
    white, gray = RGBColor(255, 255, 255), RGBColor(0x40, 0x40, 0x40)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    s = prs.slides.add_slide(blank)
    _rect(s, 0, 0, 13.333, 7.5, dark)
    _rect(s, 0.8, 3.95, 3.0, 0.08, accent)
    _text(s, title, 0.8, 2.2, 11.7, 1.6, 40, white, True, anchor=MSO_ANCHOR.BOTTOM)
    _text(s, subtitle, 0.8, 4.2, 11.7, 1.0, 20, RGBColor(0xDD, 0xDD, 0xDD))

    for no, sl in enumerate(slides, 2):
        s = prs.slides.add_slide(blank)
        _rect(s, 0, 0, 13.333, 1.1, dark)
        _rect(s, 0, 1.1, 13.333, 0.06, accent)
        _text(s, sl["title"] or title, 0.6, 0.12, 12.1, 0.9, 28, white, True, anchor=MSO_ANCHOR.MIDDLE)
        _text(s, f"{footer}", 0.6, 7.0, 8, 0.4, 11, RGBColor(0x88, 0x88, 0x88))
        _text(s, str(no), 12.0, 7.0, 0.8, 0.4, 11, RGBColor(0x88, 0x88, 0x88), align=PP_ALIGN.RIGHT)
        imgs = [p for p in sl["images"] if Path(p).is_file()]
        missing = [p for p in sl["images"] if not Path(p).is_file()]
        bullets = sl["bullets"] + [(0, f"(그림 파일 없음: {p})") for p in missing]
        x, w, top, bottom = 0.7, 11.9 if not imgs else 6.6, 1.5, 6.8
        if bullets:
            n = len(bullets)
            size = 24 if n <= 5 else 20 if n <= 8 else 16
            bh = (bottom - top) if not sl["table"] else min(0.6 * n + 0.3, 2.6)
            _text(s, bullets, x, top, w, bh, size, gray)
            top += bh + 0.1
        if sl["table"]:
            _table(s, sl["table"], x, top, w, min(0.5 * len(sl["table"]), bottom - top), dark)
        if imgs:
            ih = (6.8 - 1.5) / len(imgs)
            for k, p in enumerate(imgs):
                pic = s.shapes.add_picture(p, Inches(7.6), Inches(1.5 + k * ih), height=Inches(ih - 0.15))
                if pic.width > Inches(5.2):          # 너무 넓으면 폭 기준으로 줄이기
                    ratio = Inches(5.2) / pic.width
                    pic.width, pic.height = Inches(5.2), int(pic.height * ratio)
    prs.save(path)
    return len(prs.slides)


def run(v, ctx):
    st = ctx.settings
    outline = v["outline"]
    if v["txt"]:
        outline = Path(v["txt"]).read_text(encoding="utf-8-sig")
    if v["use_ai"]:
        n = int(v["n"] or 6)
        outline = ctx.ai(
            f"주제: {v['title']}\n회사: {st.get('company') or '전기·자동제어 공사 업체'}\n"
            f"참고 내용:\n{outline}\n\n위 주제로 슬라이드 {n}장 발표 개요를 써라. 형식 규칙: 슬라이드마다 '# 제목' 줄로 시작, "
            "항목은 '- '로 시작(슬라이드당 3~6개, 한 줄 40자 이내), 표가 더 나으면 '| 가 | 나 |' 줄 사용(첫 줄은 머리글). "
            "다른 설명 없이 개요만 출력.",
            system="너는 전기공사·PLC 자동제어 회사의 실무 문서 작성자다. 정확하고 간결한 한국어 실무 표현을 쓴다.")
    slides = parse(outline)
    if not slides:
        return Result(False, "내용이 비어 있습니다. '# 제목' 과 '- 항목' 형식으로 써 주세요.")
    sub = v["subtitle"] or " · ".join(x for x in (st.get("company"), date.today().strftime("%Y. %m. %d.")) if x)
    path = ctx.out(f"{v['title'] or '발표자료'}.pptx")
    n = build(v["title"], sub, slides, v["theme"], path, footer=st.get("company", ""))
    return Result(True, f"PPT {n}장 완성!", [str(path)])
