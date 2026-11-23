"""작업일지: 입력할 때마다 월별 엑셀 파일에 한 줄씩 쌓임."""
from datetime import date

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from office_suite.core import Field, Result

KEY = "worklog"
NAME = "📝 작업일지 기록"
DESC = "오늘 한 일을 적으면 월별 엑셀(작업일지_2026-11.xlsx)에 자동으로 쌓입니다"
ORDER = 40
COLS = ("날짜", "현장명", "날씨", "작업자", "작업 내용", "사용 자재", "특이사항")
FIELDS = [
    Field("day", "날짜 (YYYY-MM-DD)", "text", ""),
    Field("site", "현장명", "text", ""),
    Field("weather", "날씨", "choice", "맑음", choices=("맑음", "흐림", "비", "눈", "실내")),
    Field("workers", "작업자", "text", ""),
    Field("work", "작업 내용", "multiline", ""),
    Field("material", "사용 자재", "multiline", ""),
    Field("issue", "특이사항 (안전·하자 등)", "multiline", ""),
]


def run(v, ctx):
    day = (v["day"] or date.today().isoformat()).strip()
    try:
        d = date.fromisoformat(day)
    except ValueError:
        return Result(False, "날짜는 2026-11-23 형식으로 입력하세요 (비우면 오늘).")
    if not v["work"].strip():
        return Result(False, "작업 내용을 입력하세요.")
    path = ctx.out_dir / f"작업일지_{d:%Y-%m}.xlsx"
    if path.exists():
        wb = load_workbook(path)
        ws = wb.active
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = f"{d:%Y-%m}"
        ws.append(COLS)
        for c, w in zip("ABCDEFG", (12, 18, 7, 16, 45, 30, 30)):
            ws.column_dimensions[c].width = w
            ws[f"{c}1"].font = Font(bold=True, color="FFFFFF")
            ws[f"{c}1"].fill = PatternFill("solid", fgColor="1F4E79")
        ws.freeze_panes = "A2"
    ws.append((d.isoformat(), v["site"], v["weather"], v["workers"], v["work"], v["material"], v["issue"]))
    for c in ws[ws.max_row]:
        c.alignment = Alignment(wrap_text=True, vertical="top")
    try:
        wb.save(path)
    except PermissionError:
        return Result(False, f"엑셀 파일이 열려 있어 저장하지 못했습니다. 파일을 닫고 다시 눌러 주세요.\n{path}")
    return Result(True, f"{d} 작업일지 저장 완료 (이번 달 {ws.max_row - 1}건)", [str(path)])
