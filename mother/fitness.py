"""회원 운동·식단 관리: fitness/members.json → 깃허브에서 바로 보이는 관리표(.md) 생성 (토큰 0)

python -m mother fitness            # 전체 회원 관리표 생성 → fitness/routines/
python -m mother fitness --check    # 데이터 오류만 검사
"""
import json

from . import store

WEEK = ["월", "화", "수", "목", "금", "토", "일"]
SLOTS = ["아침", "점심", "저녁", "간식"]
FIT = store.ROOT / "fitness"
PAGES = "https://gogonaver12-bot.github.io/link/fitness/"


def load(path=None):
    return json.loads((path or FIT / "members.json").read_text(encoding="utf-8"))


def validate(data):
    errs, ids = [], set()
    for i, m in enumerate(data.get("members", [])):
        who = m.get("name") or f"#{i}"
        if not m.get("id"):
            errs.append(f"{who}: id 없음")
        elif m["id"] in ids:
            errs.append(f"{who}: id 중복 {m['id']}")
        ids.add(m.get("id"))
        for d, exs in (m.get("routine") or {}).items():
            if d not in WEEK:
                errs.append(f"{who}: 잘못된 요일 '{d}'")
            for e in exs:
                if not e.get("name") or not isinstance(e.get("sets"), (int, float)):
                    errs.append(f"{who}/{d}: 운동 이름·세트 확인 필요 {e}")
        if any(p.get("img") for p in m.get("photos") or []):
            errs.append(f"{who}: 사진은 저장소에 올리지 마세요(개인정보) — 앱의 '내보내기'는 자동 제외")
        if m.get("pass") and not isinstance(m["pass"].get("total"), int):
            errs.append(f"{who}: PT 이용권 총 횟수는 숫자여야 해요")
        for s in m.get("schedule") or []:
            if len(str(s.get("date", ""))) != 10:
                errs.append(f"{who}: 일정 날짜 형식(YYYY-MM-DD) 오류 {s}")
    return errs


def totals(m):
    foods = [f for s in SLOTS for f in (m.get("meals") or {}).get(s, [])]
    return sum(f.get("kcal", 0) for f in foods), sum(f.get("protein", 0) for f in foods)


def weekly_sets(m):
    return {d: sum(e.get("sets", 0) for e in (m.get("routine") or {}).get(d, [])) for d in WEEK}


def render_md(m):
    kcal, prot = totals(m)
    sets = weekly_sets(m)
    r = m.get("routine") or {}
    out = [
        f"# {m['name']} · 개인 운동 계획 관리표",
        "",
        f"- 목표: {m.get('goal', '-')} · 수준: {m.get('level', '-')} · 시작: {m.get('start', '-')}",
        f"- 체중: {m.get('weight', '-')}kg → 목표 {m.get('targetWeight', '-')}kg",
        f"- 식단: 하루 {kcal}kcal / 목표 {m.get('kcal', '-')}kcal · 단백질 {prot}g / 목표 {m.get('protein', '-')}g",
        f"- 매일 습관: {', '.join(m.get('habits') or []) or '-'}",
        f"- 📱 체크·공유 화면: {PAGES}?m={m['id']}",
        "",
        "## 주간 루틴",
        "",
        "| 요일 | 운동 | 세트×횟수 | 중량 | 1주 | 2주 | 3주 | 4주 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    pas = m.get("pass") or {}
    if pas.get("total"):
        out.insert(5, f"- PT 이용권: 총 {pas['total']}회 · 사용 {m.get('passUsed', 0)}회 · 만료 {pas.get('expiry', '-')}")
    for d in WEEK:
        exs = r.get(d, [])
        if not exs:
            out.append(f"| {d} | 휴식 | | | | | | |")
        for i, e in enumerate(exs):
            kg = f"{e['kg']}kg" if e.get("kg") else "-"
            out.append(f"| {'' if i else d} | {e['name']} | {e['sets']}×{e['reps']} | {kg} | ⬜ | ⬜ | ⬜ | ⬜ |")
    out += ["", "주간 총 세트: " + " · ".join(f"{d} {n}" for d, n in sets.items() if n) + f" (합계 {sum(sets.values())})",
            "", "## 식단 계획", "", "| 끼니 | 메뉴 | kcal | 단백질 |", "|---|---|---|---|"]
    for s in SLOTS:
        fs = (m.get("meals") or {}).get(s, [])
        menu = ", ".join(f["food"] for f in fs) or "-"
        out.append(f"| {s} | {menu} | {sum(f.get('kcal', 0) for f in fs)} | {sum(f.get('protein', 0) for f in fs)}g |")
    if m.get("coach"):
        out += ["", f"> 💬 코치 메시지 ({m['coach'][0]['date']}): {m['coach'][0]['text']}"]
    sch = sorted(m.get("schedule") or [], key=lambda x: x["date"] + x.get("time", ""))
    if sch:
        out += ["", "## 일정", ""] + [f"- {x['date']} {x.get('time', '')} {x['title']} {x.get('note', '')}".rstrip() for x in sch]
    return "\n".join(out) + "\n"


def export_all(data=None, out_dir=None):
    data = data or load()
    errs = validate(data)
    if errs:
        raise ValueError("members.json 오류: " + "; ".join(errs))
    out = out_dir or FIT / "routines"
    out.mkdir(parents=True, exist_ok=True)
    idx = ["# 회원 루틴 목록", "", f"앱: {PAGES}", "", "| 회원 | 목표 | 관리표 | 공유 링크 |", "|---|---|---|---|"]
    for m in data["members"]:
        (out / f"{m['id']}.md").write_text(render_md(m), encoding="utf-8")
        idx.append(f"| {m['name']} | {m.get('goal', '')} | [{m['id']}.md]({m['id']}.md) | {PAGES}?m={m['id']} |")
    (out / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")
    return out, len(data["members"])
