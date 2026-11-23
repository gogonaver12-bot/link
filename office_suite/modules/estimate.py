"""견적서 자동 작성 (엑셀). 엑셀에서 복사-붙여넣기한 표도 그대로 인식."""
import re
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from office_suite.core import Field, Result

KEY = "estimate"
NAME = "💰 견적서 만들기"
DESC = "한 줄에 하나씩: 품명, 규격, 단위, 수량, 단가  (엑셀 표를 복사해 붙여넣어도 됨)"
ORDER = 20
SAMPLE = """저압 배전반, 1600x800x2000, 면, 2, 3500000
CV 케이블, 4C 25sq, m, 120, 18500
배선용 차단기, 3P 100A, EA, 6, 85000
PLC 프로그램 수정, LS XGK, 식, 1, 1200000
전기공사 노무비, 내선전공, 인, 8, 280000"""
FIELDS = [
    Field("client", "받는 곳 (거래처)", "text", "○○산업(주)"),
    Field("project", "공사명", "text", "수배전반 교체 공사"),
    Field("items", "품목", "multiline", SAMPLE),
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
        try:
            if len(parts) >= 5:
                name, spec, unit, qty, price = parts[0], parts[1], parts[2], num(parts[3]), num(parts[4])
            elif len(parts) == 4:
                name, spec, unit, qty, price = parts[0], parts[1], "식", num(parts[2]), num(parts[3])
            elif len(parts) == 3:
                name, spec, unit, qty, price = parts[0], "", "식", num(parts[1]), num(parts[2])
            else:
                raise ValueError
        except ValueError:
            raise ValueError(f"이 줄을 이해하지 못했습니다 → {line.strip()}\n형식: 품명, 규격, 단위, 수량, 단가")
        items.append((name, spec, unit, qty, price))
    return items


def run(v, ctx):
    items = parse_items(v["items"])
    if not items:
        return Result(False, "품목을 한 줄 이상 입력하세요.")
    st = ctx.settings
    sub = sum(q * p for *_, q, p in items)
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
    for k, (name, spec, unit, qty, price) in enumerate(items, 1):
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
    return Result(True, f"견적서 완성! 합계 ₩{total:,.0f} (일금 {won_kor(total)}원정)\n※ 엑셀에서 수량·단가를 고치면 금액이 자동 계산됩니다.", [str(path)])
