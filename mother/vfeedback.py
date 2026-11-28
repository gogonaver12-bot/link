"""영상 피드백 핀: 폰 앱에서 멈춘 화면의 '그 자리'를 찍고 한 줄 메모 → data/video_feedback.jsonl.
쌓인 피드백은 AI가 '제작 규칙'으로 정리해 skills/production-feedback.md 에 저장 → 대본 작가·스토리 제작이 다음 영상부터 반영.
(같은 지적을 말로 여러 번 설명하지 않게 — 위치·시간이 함께 남음)"""
from . import providers, store

RULES = store.SKILLS / "production-feedback.md"


def _where(x, y):
    v = "위쪽" if y < 0.33 else "가운데" if y < 0.66 else "아래쪽"
    h = "왼쪽" if x < 0.33 else "가운데" if x < 0.66 else "오른쪽"
    return f"화면 {v}·{h}"


def add(file, t, x, y, note):
    row = {"ts": store.now().isoformat(timespec="seconds"), "file": file, "t": round(float(t), 1),
           "x": round(float(x), 3), "y": round(float(y), 3), "where": _where(float(x), float(y)), "note": note[:300]}
    store.append_jsonl("video_feedback.jsonl", row)
    return f"📍 피드백 저장: {file} {row['t']}초 {row['where']} — {row['note']} (다음 제작부터 반영)"


def rules(force=False):
    """피드백 → 제작 규칙(스킬). 새 피드백이 없으면 그대로."""
    rows = store.read_jsonl("video_feedback.jsonl")[-60:]
    if not rows:
        return "피드백 없음"
    last = rows[-1]["ts"]
    if not force and RULES.exists() and last in RULES.read_text(encoding="utf-8")[:300]:
        return "제작 규칙 최신 상태"
    notes = "\n".join(f"- [{r['file']} {r['t']}초 {r['where']}] {r['note']}" for r in rows)
    text, used = providers.complete(
        f"사용자가 영상을 보며 남긴 피드백(파일·시간·화면 위치·메모):\n{notes}\n\n"
        "같은 지적끼리 묶어, 다음 영상부터 지킬 '제작 규칙'을 번호 목록 5~12개로. 규칙마다 무엇을 어떻게(위치·크기·길이·속도·말투 등 숫자로) 바꾸는지 구체적으로, "
        "근거가 된 피드백 수를 괄호로. 한국어로 짧게.", system="너는 숏폼 영상 감독이다. 사용자 피드백을 제작 규칙으로 정리한다.", agent="vfeedback")
    RULES.write_text("---\nname: production-feedback\ndescription: \"Use when writing scripts or making shorts/story videos for this company — "
                     "the owner's own feedback turned into production rules\"\n---\n"
                     f"<!-- 자동 생성: data/video_feedback.jsonl {len(rows)}건, 마지막 {last}, {used} -->\n# 사장님 피드백 → 제작 규칙\n\n{text.strip()}\n",
                     encoding="utf-8")
    return f"📏 제작 규칙 갱신 ({len(rows)}건 → skills/production-feedback.md)"


def rules_text(limit=1200):
    if not RULES.exists():
        return ""
    t = RULES.read_text(encoding="utf-8")
    return t.split("# 사장님 피드백 → 제작 규칙", 1)[-1].strip()[:limit]
