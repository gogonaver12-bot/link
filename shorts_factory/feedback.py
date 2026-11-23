#!/usr/bin/env python3
"""자가 피드백 루프: 성과(stats.csv) -> AI 분석(무료 AI 우선 자동 선택) -> 다음 대본 N개 자동 생성.

stats.csv 열: file,title,views,avg_view_pct,likes,subs_gained
  (YouTube 스튜디오 > 분석 > 내보내기 값을 옮기거나, upload.py --stats 로 자동 수집)
사용: python feedback.py --n 5   (GEMINI/GROQ/ANTHROPIC 등 아무 키 1개면 동작)
AI 키가 하나도 없으면 규칙 기반 피드백만 출력.
"""
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPTS = ROOT / "scripts"

SCHEMA_HINT = """각 대본은 JSON 객체: {"title":"","hook":"","lines":["",...],"cta":"","description":"","tags":[""],"colors":["0xRRGGBB","0xRRGGBB"],"keywords":["자막 줄마다 1개, 순서대로 영어 검색어(예: black hole, galaxy)"]}
규칙: 한국어, 읽는 시간 25~50초, 첫 줄은 3초 안에 끝나는 강한 훅, 저작권/실존인물/허위정보 금지,
조회 상위 영상의 공통점은 강화하고 하위 영상의 패턴은 피할 것. 출력은 {"analysis":"...","scripts":[...]} 만."""


def load_stats():
    p = ROOT / "stats.csv"
    if not p.exists():
        return []
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    for r in rows:
        for k in ("views", "avg_view_pct", "likes", "subs_gained"):
            r[k] = float(r.get(k) or 0)
    return sorted(rows, key=lambda r: r["views"], reverse=True)


def rule_feedback(rows):
    if not rows:
        return "아직 데이터 없음. 최소 5개 업로드 후 48시간 뒤 stats.csv 작성."
    tips = []
    avg_ret = sum(r["avg_view_pct"] for r in rows) / len(rows)
    if avg_ret < 70:
        tips.append(f"평균 시청지속률 {avg_ret:.0f}% (<70%) → 훅 더 짧게, 전체 30초 이하로")
    if rows[0]["views"] < 1000:
        tips.append("최고 조회수 1천 미만 → 주제 바꿔 A/B 테스트(같은 날 다른 주제 3개)")
    tips.append(f"베스트: '{rows[0]['title']}' 스타일 반복 / 워스트: '{rows[-1]['title']}' 주제 중단")
    return "\n".join(tips)


def ask_ai(rows, n):
    """모든 AI 통합 라우터 사용: 무료 AI 우선(Gemini·Groq 등) → 실패 시 다음 AI → Claude."""
    sys.path.insert(0, str(ROOT.parent))
    from mother import providers
    existing = [json.loads(p.read_text(encoding="utf-8"))["title"] for p in SCRIPTS.glob("*.json")]
    prompt = (f"유튜브 숏츠 채널 성과 데이터(조회수 순):\n{json.dumps(rows[:30], ensure_ascii=False)}\n"
              f"이미 만든 제목: {existing}\n\n성과를 분석하고 다음 숏츠 대본 {n}개를 만들어줘.\n{SCHEMA_HINT}")
    try:
        text, used = providers.complete(prompt, system="JSON만 출력한다.", agent="shorts_feedback")
    except Exception as e:
        print(f"(AI 연결 없음 → 대본 생성 생략: {e})")
        return None
    print(f"🤖 사용 AI: {used}")
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    a = ap.parse_args()
    rows = load_stats()
    print("📊 규칙 피드백:\n" + rule_feedback(rows))
    res = ask_ai(rows, a.n)
    if not res:
        return
    print("\n🤖 AI 분석:\n" + res.get("analysis", ""))
    start = max([int(p.stem) for p in SCRIPTS.glob("[0-9]*.json")] or [0]) + 1
    for i, s in enumerate(res.get("scripts", [])):
        p = SCRIPTS / f"{start + i:03d}.json"
        p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📝 {p.name}: {s.get('title')}")


if __name__ == "__main__":
    sys.exit(main())
