"""자재 최저가 찾기: 네이버 쇼핑(공식 API) + 내 거래처 단가표(엑셀/CSV)를 비교해 가장 싼 곳을 정리.
결과의 '견적서 붙여넣기' 줄을 견적서 품목 칸에 붙이면 원가로 들어가고 마진율로 단가가 자동 계산됨."""
import csv
import html
import io
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from office_suite.core import Field, Result

KEY = "price"
NAME = "🔎 자재 최저가 찾기"
DESC = "품목별로 인터넷(네이버 쇼핑)과 내 거래처 단가표를 비교해 가장 싼 곳을 찾아 엑셀로 정리 (뒤에 '× 수량' 가능)"
ORDER = 25
SOURCES = ("네이버 쇼핑 + 거래처 단가표", "네이버 쇼핑만", "거래처 단가표만")
FIELDS = [
    Field("items", "찾을 품목 (한 줄에 하나)", "multiline", "CV 케이블 4C 25sq × 120\nLS 배선용차단기 ABN103c × 6\n하이박스 300x400 × 2"),
    Field("source", "어디서 찾을까", "choice", SOURCES[0], choices=SOURCES),
    Field("pricelist", "거래처 단가표 (엑셀/CSV, 시트 이름 = 거래처)", "file", ""),
    Field("top", "품목당 비교 개수", "number", 5),
    Field("exclude", "제외할 단어 (쉼표로 구분)", "text", "중고, 렌탈, 대여, 수리, 부품"),
]
API = "https://openapi.naver.com/v1/search/shop.json"
NAME_H, SPEC_H = ("품명", "품목", "자재명", "제품명", "상품명", "모델"), ("규격", "사양", "형식")
PRICE_H, VENDOR_H, UNIT_H = ("단가", "가격", "판매가", "공급가", "금액"), ("거래처", "업체", "공급사", "판매처"), ("단위",)
KEY_HELP = ("네이버 키가 없습니다. (무료) developers.naver.com → Application → 애플리케이션 등록 → "
            "사용 API '검색' 선택 → 받은 Client ID / Secret 을 [⚙ 회사 정보 설정]에 입력하세요.")


def norm(s):
    s = str(s).lower().replace("㎟", "sq").replace("mm2", "sq").replace("sqmm", "sq")
    return re.sub(r"[^0-9a-z가-힣]", "", s)


def tokens(q):
    return [t for t in (norm(x) for x in q.split()) if t]


def score(toks, text):
    t = norm(text)
    return sum(k in t for k in toks) / len(toks) if toks else 0


def matches(toks, text):
    return score(toks, text) >= (1 if len(toks) <= 2 else 0.75)


def parse_query(line):
    m = re.search(r"\s+[x×*]\s*(\d+(?:\.\d+)?)\s*$", line)
    return (line[:m.start()].strip(), float(m.group(1))) if m else (line.strip(), 1.0)


def _num(v):
    try:
        return float(re.sub(r"[^\d.]", "", str(v)) or "x")
    except ValueError:
        return None


# ── 네이버 쇼핑 ──────────────────────────────────────────────
def naver_fetch(query, cid, secret, display=80):
    req = Request(f"{API}?{urlencode({'query': query, 'display': display, 'sort': 'sim'})}",
                  headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret})
    with urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def naver_search(query, cid, secret, exclude=()):
    """관련도순으로 넉넉히 받아 → 검색어와 맞는 상품만 남기고 → 가격순 정렬 (엉뚱한 싼 부속품 제외)."""
    toks, out = tokens(query), []
    for it in naver_fetch(query, cid, secret).get("items", []):
        title = html.unescape(re.sub(r"</?b>", "", it.get("title", "")))
        price = _num(it.get("lprice"))
        if not price or any(x and x in title for x in exclude):
            continue
        if matches(toks, f"{title} {it.get('brand', '')} {it.get('maker', '')}"):
            out.append({"source": "네이버", "vendor": it.get("mallName") or "네이버", "title": title,
                        "price": price, "unit": "", "link": it.get("link", "")})
    return sorted(out, key=lambda r: r["price"])


# ── 거래처 단가표 ────────────────────────────────────────────
def _find(header, keys):
    for k in keys:
        for i, h in enumerate(header):
            if h and k in str(h):
                return i
    return None


def _rows_to_items(rows, vendor):
    for hi, row in enumerate(rows[:15]):
        ni, pi = _find(row, NAME_H), _find(row, PRICE_H)
        if ni is not None and pi is not None:
            break
    else:
        return []
    si, vi, ui = _find(row, SPEC_H), _find(row, VENDOR_H), _find(row, UNIT_H)
    cell = lambda r, i: r[i] if i is not None and i < len(r) and r[i] is not None else ""
    out = []
    for r in rows[hi + 1:]:
        name, price = cell(r, ni), _num(cell(r, pi))
        if str(name).strip() and price:
            out.append({"source": "거래처", "vendor": str(cell(r, vi) or vendor), "price": price,
                        "title": f"{name} {cell(r, si)}".strip(), "unit": str(cell(r, ui)), "link": ""})
    return out


def load_pricelist(path):
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        wb = load_workbook(p, read_only=True, data_only=True)
        return [x for ws in wb.worksheets for x in _rows_to_items([list(r) for r in ws.iter_rows(values_only=True)], ws.title)]
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp949"):            # 한글 엑셀에서 저장한 CSV는 cp949
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return _rows_to_items(list(csv.reader(io.StringIO(text))), p.stem)


def pricelist_search(query, items, exclude=()):
    toks = tokens(query)
    hit = [dict(x) for x in items if matches(toks, x["title"]) and not any(e and e in x["title"] for e in exclude)]
    return sorted(hit, key=lambda r: r["price"])


# ── 실행 ────────────────────────────────────────────────────
def run(v, ctx):
    queries = [parse_query(x) for x in v["items"].splitlines() if x.strip()]
    if not queries:
        return Result(False, "찾을 품목을 한 줄에 하나씩 입력하세요.")
    use_naver, use_list = v["source"] != SOURCES[2], v["source"] != SOURCES[1]
    cid, secret = ctx.settings.get("naver_id", ""), ctx.settings.get("naver_secret", "")
    notes, plist = [], []
    if use_list:
        if v["pricelist"]:
            plist = load_pricelist(v["pricelist"])
            notes.append(f"거래처 단가표 {len(plist)}개 품목 불러옴")
        elif not use_naver:
            return Result(False, "거래처 단가표 파일을 선택하세요. (품명·규격·단가 칸이 있는 엑셀, 시트 이름 = 거래처)")
    if use_naver and not (cid and secret):
        if not plist:
            return Result(False, KEY_HELP)
        use_naver = False
        notes.append("⚠ 네이버 키가 없어 거래처 단가표만 비교했습니다.")
    exclude = [x.strip() for x in v["exclude"].split(",") if x.strip()]
    top = max(1, int(v["top"]))
    found = []
    for q, qty in queries:
        cands = pricelist_search(q, plist, exclude) if plist else []
        if use_naver:
            try:
                cands += naver_search(q, cid, secret, exclude)
            except HTTPError as e:
                return Result(False, "네이버 키가 올바르지 않습니다. 설정을 확인하세요." if e.code in (401, 403)
                              else f"네이버 검색 오류 ({e.code})")
            except URLError:
                return Result(False, "인터넷 연결을 확인하세요.")
            time.sleep(0.12)                       # 초당 호출 제한 지키기
        found.append((q, qty, sorted(cands, key=lambda r: r["price"])[:top]))

    wb = Workbook()
    ws = wb.active
    ws.title = "최저가 요약"
    head = PatternFill("solid", fgColor="1F4E79")
    ws.append(["품목", "수량", "최저가", "금액(×수량)", "판매처", "출처", "상품명", "링크"])
    full = wb.create_sheet("전체 비교")
    full.append(["품목", "순위", "가격", "판매처", "출처", "상품명", "단위", "링크"])
    paste = wb.create_sheet("견적서 붙여넣기")
    lines, msg, total = [], [], 0
    for q, qty, c in found:
        if c:
            b = c[0]
            total += b["price"] * qty
            ws.append([q, qty, b["price"], b["price"] * qty, b["vendor"], b["source"], b["title"], b["link"]])
            msg.append(f"• {q} → {b['price']:,.0f}원  {b['vendor']} ({b['source']}, 후보 {len(c)}개)")
            lines.append(f"{q}, , {b['unit'] or 'EA'}, {qty:g}, , {b['price']:.0f}")
        else:
            ws.append([q, qty, None, None, "못 찾음", "", "검색어를 짧게 바꿔 보세요", ""])
            msg.append(f"• {q} → 못 찾음 (검색어를 짧게)")
        for rank, r in enumerate(c, 1):
            full.append([q, rank, r["price"], r["vendor"], r["source"], r["title"], r["unit"], r["link"]])
    for line in lines:
        paste.append([line])
    for sh, widths in ((ws, (26, 7, 12, 14, 18, 8, 50, 40)), (full, (26, 6, 12, 18, 8, 50, 8, 40))):
        for c in sh[1]:
            c.font, c.fill = Font(bold=True, color="FFFFFF"), head
        for i, w in enumerate(widths):
            sh.column_dimensions[chr(65 + i)].width = w
        for row in sh.iter_rows(min_row=2):
            for c in row:
                if isinstance(c.value, (int, float)) and c.column_letter in ("C", "D"):
                    c.number_format = "#,##0"
                if isinstance(c.value, str) and c.value.startswith("http"):
                    c.hyperlink, c.font = c.value, Font(color="0563C1", underline="single")
    paste.column_dimensions["A"].width = 70
    path = ctx.out("최저가비교.xlsx")
    wb.save(path)
    out = notes + msg + [f"\n최저가 합계(수량 반영): {total:,.0f}원",
                         "※ 인터넷 가격은 포장 단위(1m·1롤·1박스)와 배송비가 다를 수 있으니 꼭 확인하세요."]
    if lines:
        out += ["\n▼ 견적서 품목 칸에 그대로 붙여넣기 (원가로 들어가고 마진율로 단가 자동 계산)"] + lines
    return Result(True, "\n".join(out), [str(path)])
