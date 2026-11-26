"""자동 진단의사: 최근 에러를 Superpowers 'systematic-debugging' 방식(원인 조사 → 패턴 → 가설 → 고칠 점)으로 진단해 보고서로 남긴다.
코드를 직접 고치지는 않는다(사람·개발 세션이 보고서를 보고 고침). 매일 자동 실행 + `python -m mother doctor`.
"""
import re
from collections import Counter

from . import providers, store

KNOWN = [  # 원인이 이미 알려진(코드로 고칠 게 아닌) 에러 → AI 안 부르고 바로 안내
    (r"credit balance|insufficient_quota", "AI 충전 잔액 부족 — 무료 AI로 자동 전환 중(Claude는 12시간마다 재확인). 쓰려면 콘솔에서 충전"),
    (r"uploadLimitExceeded|업로드 한도", "유튜브 하루 업로드 한도 — 다음 날 자동 재시도"),
    (r"\b429\b|quota", "무료 사용량 초과 — 다른 AI·다음 날로 자동 전환"),
]


def _sig(err):
    return re.sub(r"\d+|0x[0-9a-f]+|'[^']*'|\"[^\"]*\"", "#", (err or "").split("\n")[0])[:120]


def _skill():
    f = store.SKILLS / "superpowers-systematic-debugging.md"
    return f.read_text(encoding="utf-8")[:6000] if f.exists() else ""


def run(days=2, limit=4):
    cutoff = (store.now() - __import__("datetime").timedelta(days=days)).isoformat(timespec="seconds")
    errs = [e for e in store.read_jsonl("errors.jsonl") if e.get("ts", "") >= cutoff]
    if not errs:
        return "🩺 최근 에러 없음"
    groups = Counter(_sig(e.get("error")) for e in errs)
    lines = [f"# 🩺 자동 진단 {store.today()} — 최근 {days}일 에러 {len(errs)}건 · 종류 {len(groups)}개", ""]
    asked = 0
    for sig, cnt in groups.most_common():
        sample = next(e for e in reversed(errs) if _sig(e.get("error")) == sig)
        known = next((msg for pat, msg in KNOWN if re.search(pat, sample.get("error", ""), re.I)), None)
        lines.append(f"## {cnt}회 · `{sample.get('cmd', '')}` · {sig[:80]}")
        if known:
            lines += [f"- ✅ 알려진 원인: {known}", ""]
            continue
        if asked >= limit:
            lines += ["- (오늘 진단 한도 초과 — 내일 이어서)", ""]
            continue
        asked += 1
        prompt = (f"[에러]\n명령: {sample.get('cmd')}\n{sample.get('error', '')[:800]}\n\n[스택]\n{sample.get('trace', '')[-2500:]}\n\n"
                  "위 방법론(Phase 1 근본 원인 조사 → Phase 2 패턴 → Phase 3 가설 하나 → Phase 4 고칠 점)대로 진단하라. "
                  "추측과 확인된 사실을 구분하고, 고칠 파일·함수와 최소 수정안, 재발 방지 테스트 1개를 한국어로 짧게.")
        try:
            text, used = providers.complete(prompt, system=("너는 이 저장소의 디버깅 담당이다. 아래 방법론을 따른다.\n" + _skill())[:7000],
                                            agent="doctor")
            lines += [text.strip(), f"\n> 진단 AI: {used}", ""]
        except Exception as e:
            lines += [f"- 진단 실패: {str(e)[:120]}", ""]
    d = store.REPORTS / "doctor"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{store.today()}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"🩺 에러 {len(errs)}건(종류 {len(groups)}개) 진단 → reports/doctor/{store.today()}.md (AI 진단 {asked}건)"
