"""상품 제작 라인: 사업 아이디어 → 판매 가능한 결과물(목차·원고·PDF) + 판매 페이지 문구.

무료 AI(Gemini·Groq 등)로도 끝까지 돌도록 '한 번에 한 장씩' 단발 호출로 만든다(도구 루프 없음).
"""
import re

import requests

from . import llm, providers, store

LANG_NAME = {"ko": "한국어", "en": "English", "ja": "日本語"}
OUTLINE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["title", "subtitle", "target", "price", "sections"],
    "properties": {
        "title": {"type": "string", "description": "검색·클릭을 부르는 상품 제목"},
        "subtitle": {"type": "string"},
        "target": {"type": "string", "description": "구매자 한 줄 묘사"},
        "price": {"type": "string", "description": "추천 판매가와 근거 한 줄"},
        "sections": {"type": "array", "description": "5~8개 장", "items": {
            "type": "object", "additionalProperties": False, "required": ["title", "points"],
            "properties": {"title": {"type": "string"}, "points": {"type": "array", "items": {"type": "string"}}}}},
    },
}


def _idea(idea_id):
    for i in store.load_json("ideas.json", []):
        if i["id"] == idea_id:
            return i
    raise ValueError(f"사업 {idea_id} 없음 (biz list 로 확인)")


def _lang(idea):
    blob = f"{idea.get('market', '')} {idea.get('platform', '')}".upper()
    for m in store.cfg()["markets"]:
        if m["code"] in blob:
            return m["lang"]
    return store.cfg()["report_lang"]


def _slug(s):
    return re.sub(r"[^\w가-힣ぁ-んァ-ン一-龥]+", "-", s)[:40].strip("-") or "section"


def make(idea_id, pages=30):
    idea = _idea(idea_id)
    lang = LANG_NAME.get(_lang(idea), "한국어")
    out = store.WORKSPACE / "products" / idea_id
    out.mkdir(parents=True, exist_ok=True)
    brief = (f"사업: {idea['title']}\n플랫폼: {idea.get('platform')}\n수익 구조: {idea.get('model')}\n"
             f"첫 행동: {idea.get('first_step')}\n근거: {idea.get('evidence', '')[:400]}")
    outline = llm.ask_json("worker", f"너는 잘 팔리는 디지털 상품 기획자다. 결과물 언어: {lang}.",
                           f"{brief}\n\n이 사업으로 바로 판매할 수 있는 결과물(전자책·가이드·템플릿·서비스 소개서 중 가장 맞는 것) "
                           f"약 {pages}쪽 분량의 목차를 설계하라. 각 장은 구매자가 바로 따라 할 수 있는 실전 내용으로.",
                           OUTLINE_SCHEMA, agent="product_planner")
    sections = outline["sections"][:8]
    for sec in sections:  # '1장. 제목' → '제목' (번호 중복 방지)
        sec["title"] = re.sub(r"^\s*(제?\s*\d+\s*장|chapter\s*\d+|\d+)\s*[.:)\-]?\s*", "", sec["title"], flags=re.I) or sec["title"]
    per = max(1200, pages * 550 // max(1, len(sections)))
    (out / "00-목차.md").write_text(f"# {outline['title']}\n{outline['subtitle']}\n\n- 대상: {outline['target']}\n- 가격: {outline['price']}\n\n"
                                    + "\n".join(f"{n}. {s['title']}" for n, s in enumerate(sections, 1)) + "\n", encoding="utf-8")
    texts, used = [], set()
    for n, s in enumerate(sections, 1):
        text, model = providers.complete(
            f"상품: {outline['title']} — {outline['subtitle']}\n대상: {outline['target']}\n"
            f"지금 쓸 장: {n}장 {s['title']}\n다룰 점: {'; '.join(s['points'])}\n\n"
            f"이 장의 본문을 {lang}로 약 {per}자 써라. 실제 예시·단계별 방법·체크리스트·복붙해서 쓸 수 있는 프롬프트나 템플릿을 넣고, "
            f"군더더기·과장·근거 없는 수익 약속은 빼라. 마크다운, 첫 줄은 '## {n}. {s['title']}'.",
            system=f"너는 실전 위주로 쉽게 쓰는 전문 작가다. {lang}로만 쓴다.", agent="product_writer")
        used.add(model)
        texts.append((s["title"], text))
        (out / f"{n:02d}-{_slug(s['title'])}.md").write_text(text + "\n", encoding="utf-8")
    listing, _ = providers.complete(
        f"상품: {outline['title']} — {outline['subtitle']}\n대상: {outline['target']}\n가격 제안: {outline['price']}\n"
        f"목차: {' / '.join(s['title'] for s in sections)}\n플랫폼: {idea.get('platform')}\n\n"
        f"이 플랫폼에 그대로 붙여 넣을 판매 페이지를 {lang}로 써라: 제목(40자 안), 한 줄 소개, 상세 설명(문제→해결→구성→대상→혜택), "
        f"가격 3단계(기본/표준/프리미엄 구성과 금액), 자주 묻는 질문 5개, 검색 태그 10개. 허위·과장 금지. 마크다운.",
        system="너는 전환율 높은 판매 페이지 카피라이터다.", agent="product_sales")
    (out / "판매페이지.md").write_text(listing + "\n", encoding="utf-8")
    pdf = build_pdf(out / "product.pdf", outline, texts, lang)
    files = sorted(p.name for p in out.iterdir())
    ideas = store.load_json("ideas.json", [])
    for i in ideas:
        if i["id"] == idea_id:
            i["product"] = {"made": store.today(), "title": outline["title"], "dir": f"workspace/products/{idea_id}",
                            "pdf": f"workspace/products/{idea_id}/product.pdf" if pdf else None, "files": files}
    store.save_json("ideas.json", ideas)
    rp = store.REPORTS / f"{store.now():%Y%m%d-%H%M}-상품-{idea_id}.md"
    rp.write_text(f"# 상품 완성: {outline['title']}\n{outline['subtitle']}\n\n- 사업: {idea_id} {idea['title']}\n"
                  f"- 분량: {len(sections)}장 · 약 {sum(len(t) for _, t in texts):,}자" + (" · PDF 생성" if pdf else "") +
                  f"\n- 가격 제안: {outline['price']}\n- 만든 AI: {', '.join(sorted(used))}\n- 파일: `workspace/products/{idea_id}/`\n\n"
                  f"## 다음 할 일\n- 원고를 한 번 읽고 내 경험·사례를 한두 줄씩 더하기\n- 판매페이지.md 를 {idea.get('platform')}에 붙여 넣고 PDF 첨부\n"
                  f"- 팔리면 앱 💵매출 기록\n\n## 판매 페이지\n{listing}\n", encoding="utf-8")
    return {"title": outline["title"], "sections": len(sections), "chars": sum(len(t) for _, t in texts),
            "pdf": bool(pdf), "report": f"reports/{rp.name}", "models": sorted(used)}


def rebuild_pdf(idea_id):
    """AI 호출 없이 저장된 원고로 PDF만 다시 만들기 (토큰 0)."""
    d = store.WORKSPACE / "products" / idea_id
    head = (d / "00-목차.md").read_text(encoding="utf-8").splitlines()
    outline = {"title": head[0].lstrip("# ").strip(), "subtitle": head[1].strip() if len(head) > 1 else ""}
    texts = []
    for f in sorted(d.glob("[0-9][0-9]-*.md")):
        if f.name.startswith("00-"):
            continue
        body = f.read_text(encoding="utf-8")
        first = next((l for l in body.splitlines() if l.startswith("#")), f.stem[3:])
        texts.append((re.sub(r"^#+\s*(\d+\.\s*)?", "", first).strip(), body))
    return build_pdf(d / "product.pdf", outline, texts, LANG_NAME.get(_lang(_idea(idea_id)), "한국어"))


# ───────────────────────── PDF ─────────────────────────
FONTS = {"R": "NanumGothic-Regular.ttf", "B": "NanumGothic-Bold.ttf"}
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/nanumgothic/"


def _fonts():
    d = store.DATA / "cache" / "fonts"
    d.mkdir(parents=True, exist_ok=True)
    for f in FONTS.values():
        if not (d / f).exists():
            r = requests.get(FONT_URL + f, timeout=60)
            r.raise_for_status()
            (d / f).write_bytes(r.content)
    return {k: d / f for k, f in FONTS.items()}


KEYCAP = {f"{d}\ufe0f\u20e3": f"{d}." for d in "0123456789"}
CIRCLED = {chr(0x2460 + i): f"({i + 1})" for i in range(20)}
SPACES = {"\u202f": " ", "\u00a0": " ", "\u2009": " ", "\u2011": "-", "\u2013": "-", "\u2014": "-", "\u2192": "->", "\u2190": "<-",
          "\u2714": "v", "\u2705": "v", "\u274c": "x", "\u2610": "[ ]", "\u2611": "[v]"}


def _clean(t):
    for a, b in {**KEYCAP, **CIRCLED, **SPACES}.items():
        t = t.replace(a, b)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", t)  # 링크는 글자만
    t = re.sub(r"\*\*|__|`", "", t)
    return "".join(ch for ch in t if ord(ch) < 0x2600 or 0x3000 <= ord(ch) <= 0xFFEF and ch != "\ufe0f")


def _table(pdf, rows):
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    pdf.set_font("N", "", 9.5)
    try:
        from fpdf.fonts import FontFace
        head = FontFace(family="N", emphasis="BOLD", fill_color=(225, 238, 250))
        pdf.set_fill_color(255, 255, 255)
        with pdf.table(text_align="LEFT", line_height=5.6, first_row_as_headings=True, headings_style=head,
                       padding=1.6, cell_fill_color=(246, 250, 253), cell_fill_mode="ROWS") as t:
            for r in rows:
                row = t.row()
                for c in r:
                    row.cell(c)
    except Exception:  # 표가 너무 넓으면 줄글로
        for r in rows:
            pdf.multi_cell(0, 6, " | ".join(r), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def build_pdf(path, outline, texts, lang="한국어"):
    """마크다운 원고 → 표지·목차·본문 PDF (한글 나눔고딕): 제목·목록·표·인용·코드 블록 지원."""
    if lang == "日本語":
        return None
    try:
        from fpdf import FPDF
        f = _fonts()
    except Exception:
        return None
    pdf = FPDF(format="A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(True, 20)
    pdf.add_font("N", "", str(f["R"]))
    pdf.add_font("N", "B", str(f["B"]))
    pdf.add_page()
    pdf.set_fill_color(14, 30, 52)
    pdf.rect(0, 0, 210, 297, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_y(95)
    pdf.set_font("N", "B", 24)
    pdf.multi_cell(0, 12, _clean(outline["title"]), align="C")
    pdf.ln(6)
    pdf.set_text_color(130, 215, 255)
    pdf.set_font("N", "", 13)
    pdf.multi_cell(0, 8, _clean(outline["subtitle"]), align="C")
    pdf.set_text_color(20, 20, 20)
    pdf.set_fill_color(255, 255, 255)
    pdf.add_page()
    pdf.set_font("N", "B", 18)
    pdf.cell(0, 12, "목차" if lang == "한국어" else "Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("N", "", 12)
    for n, (title, _) in enumerate(texts, 1):
        pdf.multi_cell(0, 9, _clean(f"{n}. {title}"), new_x="LMARGIN", new_y="NEXT")
    for _, text in texts:
        pdf.add_page()
        table, code = [], None
        for raw in text.splitlines() + [""]:
            s = _clean(raw).rstrip()
            if s.strip().startswith("```"):
                if code is None:
                    code = []
                else:
                    pdf.set_font("N", "", 10)
                    pdf.set_fill_color(240, 244, 248)
                    pdf.multi_cell(0, 6, "\n".join(code) or " ", fill=True, new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)
                    code = None
                continue
            if code is not None:
                code.append(s)
                continue
            if re.match(r"^\s*\|.*\|\s*$", s):
                if not re.match(r"^\s*\|[\s:|-]+\|\s*$", s):
                    table.append([c.strip() for c in s.strip().strip("|").split("|")])
                continue
            if table:
                _table(pdf, table)
                table = []
            if not s.strip():
                pdf.ln(2.5)
                continue
            m = re.match(r"^(#{1,4})\s+(.*)", s)
            if m:
                pdf.ln(2)
                pdf.set_font("N", "B", {1: 18, 2: 16, 3: 13}.get(len(m.group(1)), 12))
                pdf.set_text_color(14, 60, 110) if len(m.group(1)) <= 2 else pdf.set_text_color(20, 20, 20)
                pdf.multi_cell(0, 9, m.group(2), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(20, 20, 20)
                pdf.ln(1)
                continue
            q = re.match(r"^>\s?(.*)", s)
            if q:
                pdf.set_font("N", "", 11)
                pdf.set_fill_color(232, 246, 255)
                pdf.multi_cell(0, 6.6, "  " + q.group(1), fill=True, new_x="LMARGIN", new_y="NEXT")
                pdf.ln(1)
                continue
            b = re.match(r"^\s*[-*+]\s+(.*)", s)
            pdf.set_font("N", "", 11)
            pdf.multi_cell(0, 6.6, ("• " + b.group(1)) if b else s.strip(), new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))
    return path
