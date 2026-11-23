"""견적서 자동 작성 (엑셀). 엑셀에서 복사-붙여넣기한 표도 그대로 인식."""
import math
import re
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from office_suite.core import Field, Result

KEY = "estimate"
NAME = "💰 견적서 만들기"
DESC = ("한 줄에 하나씩: 품명, 규격, 단위, 수량, 단가, 원가(선택)  — 단가를 비우면 원가×마진율로 자동 계산, "
        "원가를 넣으면 내부용 마진분석 파일도 따로 생성")
ORDER = 20
SAMPLE = """저압 배전반, 1600x800x2000, 면, 2, 3500000, 2800000
CV 케이블, 4C 25sq, m, 120, , 15200
배선용 차단기, 3P 100A, EA, 6, , 61000
PLC 프로그램 수정, LS XGK, 식, 1, 1200000
전기공사 노무비, 내선전공, 인, 8, 280000, 230000"""
FIELDS = [
    Field("client", "받는 곳 (거래처)", "text", "○○산업(주)"),
    Field("project", "공사명", "text", "수배전반 교체 공사"),
    Field("items", "품목", "multiline", SAMPLE),
    Field("margin", "목표 마진율 (%) — 단가 빈칸 품목에 적용", "number", 20,
          help="마진율 = 이익 ÷ 판매가. 20%면 원가 8만원 → 단가 10만원"),
    Field("overhead", "일반관리비 (%)", "number", 0),
    Field("profit", "이윤 (%)", "number", 0),
    Field("vat", "부가세 10% 포함", "check", True),
    Field("valid", "견적 유효기간", "text", "견적일로부터 30일"),
    Field("note", "비고", "multiline", "현장 여건에 따라 변동될 수 있음"),
]
_D = "영일이삼사오육칠팔구"


def won_kor(n):
    """1234500 → 일백이십삼만사천오백"""
    n = int(round(n))
    if n <= 0:
        return "영"
    out, big = "", ["", "만", "억", "조", "경"]
    for i in range(len(big)):
        chunk, n = n % 10000, n // 10000
        s = "".join(_D[int(d)] + u for d, u in zip(f"{chunk:04d}", ("천", "백", "십", "")) if d != "0")
        out = (s + big[i] if chunk else "") + out
        if not n:
            break
    return out


def parse_items(text):
    items = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if "\t" in line:
            parts = line.split("\t")
        elif "|" in line:
            parts = line.strip("|").split("|")
        else:
            parts = re.sub(r"(\d),(?=\d{3}(?!\d))", r"\1", line).split(",")   # 1,000 → 1000
        parts = [p.strip() for p in parts]
        num = lambda s: float(s.replace(",", "").replace("원", "") or 0)
        cost = 0.0
        try:
            if len(parts) >= 6:
                name, spec, unit, qty, price, cost = parts[0], parts[1], parts[2], num(parts[3]), num(parts[4]), num(parts[5])
            elif len(parts) == 5:
                name, spec, unit, qty, price = parts[0], parts[1], parts[2], num(parts[3]), num(parts[4])
            elif len(parts) == 4:
                name, spec, unit, qty, price = parts[0], parts[1], "식", num(parts[2]), num(parts[3])
            elif len(parts) == 3:
                name, spec, unit, qty, price = parts[0], "", "식", num(parts[1]), num(parts[2])
            else:
                raise ValueError
        except ValueError:
            raise ValueError(f"이 줄을 이해하지 못했습니다 → {line.strip()}\n형식: 품명, 규격, 단위, 수량, 단가, 원가")
        items.append((name, spec, unit, qty, price, cost))
    return items


def price_from_margin(cost, margin_pct):
    """원가와 마진율(판매가 기준)로 단가 계산, 10원 단위 올림."""
    return math.ceil(cost / (1 - margin_pct / 100) / 10) * 10


def apply_margin(items, margin_pct):
    out = []
    for name, spec, unit, qty, price, cost in items:
        if not price:
            if not cost:
                raise ValueError(f"'{name}' 단가와 원가가 둘 다 비어 있습니다.")
            if not 0 < margin_pct < 100:
                raise ValueError(f"'{name}' 단가가 비어 있습니다. 목표 마진율(0~100%)을 넣거나 단가를 적어 주세요.")
            price = price_from_margin(cost, margin_pct)
        out.append((name, spec, unit, qty, price, cost))
    return out


def run(v, ctx):
    try:
        items = apply_margin(parse_items(v["items"]), v["margin"])
    except ValueError as e:
        return Result(False, str(e))
    if not items:
        return Result(False, "품목을 한 줄 이상 입력하세요.")
    st = ctx.settings
    sub = sum(q * p for *_, q, p, _c in items)
    oh = round(sub * v["overhead"] / 100)
    pf = round((sub + oh) * v["profit"] / 100)
    supply = sub + oh + pf
    vat = round(supply * 0.1) if v["vat"] else 0
    total = supply + vat

    wb = Workbook()
    ws = wb.active
    ws.title = "견적서"
    thin = Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)
    head = PatternFill("solid", fgColor="1F4E79")
    for col, w in zip("ABCDEFGH", (6, 26, 20, 7, 9, 14, 16, 14)):
        ws.column_dimensions[col].width = w
    ws.merge_cells("A1:H1")
    ws["A1"] = "견   적   서"
    ws["A1"].font = Font(size=24, bold=True)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.row_dimensions[1].height = 40
    info = [("견적일", date.today().strftime("%Y년 %m월 %d일")), ("받는 곳", f"{v['client']} 귀하"),
            ("공사명", v["project"]), ("유효기간", v["valid"])]
    mine = [("상호", st.get("company")), ("대표자", st.get("ceo")), ("사업자번호", st.get("biz_no")),
            ("전화", st.get("phone")), ("주소", st.get("address"))]
    for i, (k, val) in enumerate(info, 3):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.merge_cells(start_row=i, start_column=2, end_row=i, end_column=3)
        ws.cell(i, 2, val)
    for i, (k, val) in enumerate(mine, 3):
        ws.cell(i, 5, k).font = Font(bold=True)
        ws.merge_cells(start_row=i, start_column=6, end_row=i, end_column=8)
        ws.cell(i, 6, val or "")
    r = 9
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    ws.cell(r, 1, f"합계금액 :  일금 {won_kor(total)}원정  (₩{total:,.0f})" + ("  ※ 부가세 포함" if v["vat"] else "  ※ 부가세 별도"))
    ws.cell(r, 1).font = Font(size=14, bold=True, color="C00000")
    ws.row_dimensions[r].height = 28

    r = 11
    for j, h in enumerate(("No", "품명", "규격", "단위", "수량", "단가", "금액", "비고"), 1):
        c = ws.cell(r, j, h)
        c.font, c.fill, c.border = Font(bold=True, color="FFFFFF"), head, box
        c.alignment = Alignment(horizontal="center")
    first = r + 1
    for k, (name, spec, unit, qty, price, _cost) in enumerate(items, 1):
        r += 1
        for j, val in enumerate((k, name, spec, unit, qty, price, f"=E{r}*F{r}", ""), 1):
            c = ws.cell(r, j, val)
            c.border = box
            if j >= 5 and j <= 7:
                c.number_format = "#,##0.##" if j == 5 else "#,##0"
    last = r
    rows = [("소계", f"=SUM(G{first}:G{last})")]
    if v["overhead"]:
        rows.append((f"일반관리비 ({v['overhead']:g}%)", f"=ROUND(G{last + 1}*{v['overhead']}/100,0)"))
    if v["profit"]:
        base = f"(G{last + 1}+G{last + 2})" if v["overhead"] else f"G{last + 1}"
        rows.append((f"이윤 ({v['profit']:g}%)", f"=ROUND({base}*{v['profit']}/100,0)"))
    rows.append(("공급가액", f"=SUM(G{last + 1}:G{last + len(rows)})"))
    if v["vat"]:
        rows.append(("부가세 (10%)", f"=ROUND(G{last + len(rows)}*0.1,0)"))
        rows.append(("합계", f"=G{last + len(rows) - 1}+G{last + len(rows)}"))
    for label, formula in rows:
        r += 1
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
        ws.cell(r, 1, label).alignment = Alignment(horizontal="right")
        ws.cell(r, 1).font = Font(bold=True)
        c = ws.cell(r, 7, formula)
        c.number_format, c.font = "#,##0", Font(bold=True)
        for j in range(1, 9):
            ws.cell(r, j).border = box
    if v["note"]:
        r += 2
        ws.cell(r, 1, "비고").font = Font(bold=True)
        for line in v["note"].splitlines():
            ws.cell(r, 2, line)
            r += 1
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    path = ctx.out(f"견적서_{v['client']}.xlsx")
    wb.save(path)
    msg = [f"견적서 완성! 합계 ₩{total:,.0f} (일금 {won_kor(total)}원정)", "※ 엑셀에서 수량·단가를 고치면 금액이 자동 계산됩니다."]
    files = [str(path)]
    if any(c for *_, c in items):
        mpath, m = margin_report(items, oh + pf, supply, v, ctx)
        files.append(str(mpath))
        msg += ["", f"📈 예상 마진 (부가세 제외): 매출 ₩{supply:,.0f} − 원가 ₩{m['cost']:,.0f} = 이익 ₩{m['profit']:,.0f}",
                f"   마진율 {m['rate']:.1f}%  (원가 대비 {m['markup']:.1f}%)"]
        if m["loss"]:
            msg.append("⚠ 원가보다 싸게 파는 품목: " + ", ".join(m["loss"]))
        if m["missing"]:
            msg.append(f"⚠ 원가 미입력 {m['missing']}개 품목 → 실제 마진은 이보다 낮습니다")
        msg.append("🔒 마진분석 파일은 내부용입니다. 거래처에는 견적서 파일만 보내세요.")
    return Result(True, "\n".join(msg), files)


def margin_report(items, extra, supply, v, ctx):
    """내부용 마진분석 엑셀 (거래처용 견적서와 별도 파일)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "마진분석(내부용)"
    ws.append([f"마진분석 — {v['client']} / {v['project']}  (내부용, 외부 발송 금지)"])
    ws["A1"].font = Font(size=14, bold=True, color="C00000")
    hdr = ("No", "품명", "규격", "수량", "단가", "판매금액", "원가", "원가금액", "이익", "마진율", "원가대비")
    ws.append([])
    ws.append(hdr)
    for c in ws[3]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="375623")
    for col, w in zip("ABCDEFGHIJK", (5, 24, 16, 7, 12, 14, 12, 14, 14, 9, 9)):
        ws.column_dimensions[col].width = w
    loss, cost_total = [], 0
    for k, (name, spec, unit, qty, price, cost) in enumerate(items, 1):
        r = ws.max_row + 1
        has = bool(cost)
        cost_total += qty * cost
        if has and price < cost:
            loss.append(name)
        ws.append([k, name, spec, qty, price, f"=D{r}*E{r}", cost if has else "미입력",
                   f"=D{r}*G{r}" if has else 0, f"=F{r}-H{r}" if has else "",
                   f"=IF(F{r}=0,0,I{r}/F{r})" if has else "", f"=IF(H{r}=0,0,I{r}/H{r})" if has else ""])
    first, last = 4, ws.max_row
    rows = [("품목 합계", f"=SUM(F{first}:F{last})", f"=SUM(H{first}:H{last})"),
            ("일반관리비·이윤 (원가 없음)", extra, 0)]
    for label, sales, cost in rows:
        ws.append(["", label, "", "", "", sales, "", cost])
    t = ws.max_row + 1
    ws.append(["", "합계 (공급가액)", "", "", "", f"=F{t - 2}+F{t - 1}", "", f"=H{t - 2}+H{t - 1}",
               f"=F{t}-H{t}", f"=IF(F{t}=0,0,I{t}/F{t})", f"=IF(H{t}=0,0,I{t}/H{t})"])
    for c in ws[t]:
        c.font = Font(bold=True)
    for row in ws.iter_rows(min_row=4):
        for c in row:
            if c.column_letter in "EFGHI":
                c.number_format = "#,##0"
            elif c.column_letter in "JK":
                c.number_format = "0.0%"
    profit = supply - cost_total
    path = ctx.out(f"마진분석_{v['client']}_내부용.xlsx")
    wb.save(path)
    return path, {"cost": cost_total, "profit": profit, "rate": profit / supply * 100 if supply else 0,
                  "markup": profit / cost_total * 100 if cost_total else 0, "loss": loss,
                  "missing": sum(1 for *_, c in items if not c)}
