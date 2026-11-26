"""PC 렌더 쇼츠 (JARVIS-VIDEO-FACTORY feat/video-unified: 호러 3D · AI 뉴스).
클라우드: 브리프 → 대본(plan JSON, 영상 공장 규칙 그대로 검사) → jarvis/local_jobs.json 대기열.
PC: tools/local_runner/run_local_jobs.bat 가 대기열을 받아 렌더(Supertonic TTS·Blender 등은 PC에만 있음) → 폰 앱 '방금 만든 영상'.
"""
import json
import re

from . import providers, store

JOBS = store.ROOT / "jarvis" / "local_jobs.json"
PLANS = store.ROOT / "jarvis" / "local_plans"
KINDS = {"horror": "호러 3D (복도·문구멍·그림자 연출)", "ainews": "AI 뉴스 (공개 출처 사실만, 끝 화면 출처 표기)"}


def validate(plan, kind):
    """영상 공장 validate_horror / validate_v2 / validate_plan 규칙을 그대로 옮김."""
    if not isinstance(plan, dict) or not isinstance(plan.get("stories"), list) or len(plan["stories"]) != 1:
        raise ValueError("이야기는 정확히 1개")
    st = plan["stories"][0]
    if kind == "horror" and not re.fullmatch(r"[a-z0-9_]{1,24}", str(st.get("id", ""))):
        raise ValueError("id는 영문 소문자·숫자·_ 1~24자")
    if kind == "ainews":
        st["id"] = "signal"  # 뉴스 렌더러 테마
        if not str(st.get("source", "")).startswith("출처"):
            raise ValueError("source는 '출처: …'로 시작")
    if not isinstance(st.get("title"), str) or not 1 <= len(st["title"]) <= 16:
        raise ValueError("title 1~16자")
    hook = st.get("hook")
    if not (isinstance(hook, list) and 1 <= len(hook) <= 2 and all(isinstance(h, str) and 1 <= len(h) <= 8 for h in hook)):
        raise ValueError("hook은 1~2줄, 줄마다 1~8자")
    sc = st.get("scenes")
    if not isinstance(sc, list) or len(sc) != 5:
        raise ValueError("장면은 정확히 5개")
    for s in sc:
        en, ko = s.get("en"), s.get("ko")
        if not isinstance(en, str) or not 5 <= len(en.split()) <= 22 or not en.isascii():
            raise ValueError(f"en은 영어 5~22단어(ASCII): {str(en)[:40]}")
        if not isinstance(ko, str) or not 1 <= len(ko) <= 48 or not re.search("[가-힣]", ko):
            raise ValueError(f"ko는 한국어 1~48자: {str(ko)[:40]}")
        if not isinstance(s.get("key"), str) or s["key"] not in ko:
            raise ValueError(f"key는 ko 안의 문구여야 함: {s.get('key')}")
        if not isinstance(s.get("tag"), str) or not 1 <= len(s["tag"]) <= 16:
            raise ValueError("tag 1~16자")
        if any(ord(c) < 32 for c in en + ko):
            raise ValueError("제어 문자 금지")
    return plan


def _news_context():
    items = [n for n in store.load_json("news.json", []) if not n.get("flag")][-25:]
    return "\n".join(f"- {n.get('title')} ({n.get('source')}) {n.get('url')}" for n in items)


def plan(kind, brief, speed=None):
    if kind not in KINDS:
        return f"종류: {', '.join(KINDS)}"
    rule = ('JSON 하나만: {"stories":[{"id":"영문소문자_숫자_밑줄","title":"1~16자","hook":["8자 이하","8자 이하"],'
            '"scenes":[{"ko":"한국어 1~48자","en":"English 5-22 words, ASCII only","key":"ko 안에 그대로 있는 핵심 문구","tag":"1~16자"}]}]} '
            "— 장면 정확히 5개, 마지막 장면에 반전.")
    if kind == "ainews":
        rule += (' "source":"출처: 매체1 · 매체2" 필드 필수. 아래 소식에 있는 사실만 쓰고 지어내지 말 것.\n[오늘 소식]\n' + _news_context())
    else:
        rule += " 오리지널 이야기(기존 작품·실존 인물 금지), 잔혹 묘사 대신 긴장감."
    last, used = None, ""
    for k in range(3):
        prompt = f"[{KINDS[kind]}] 쇼츠 대본.\n브리프: {brief}\n{rule}" + (f"\n이전 시도 오류: {last} — 고쳐서 다시." if last else "")
        try:
            if k == 0:
                text, used = providers.complete(prompt, system="너는 쇼츠 대본 작가다. JSON만 출력한다.", agent="local_shorts")
                from .story import parse
                p = parse(text)
            else:
                p, used = providers.json_complete("너는 쇼츠 대본 작가다.", prompt, {"type": "object"}, agent="local_shorts"), "무료 AI(JSON 모드)"
            validate(p, kind)
            break
        except Exception as e:
            last, p = str(e)[:160], None
    if not p:
        return f"⚠️ 대본이 규칙을 못 맞춤: {last}"
    st = p["stories"][0]
    PLANS.mkdir(parents=True, exist_ok=True)
    jid = f"{store.today().replace('-', '')}-{kind}-{st['id'] if kind == 'horror' else re.sub(r'[^a-z0-9]+', '', brief.lower())[:12] or 'news'}"
    f = PLANS / f"{jid}.json"
    f.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    jl = [j for j in jobs() if j["id"] != jid] + [{"id": jid, "kind": kind, "plan": f"jarvis/local_plans/{f.name}", "speed": speed,
                                                   "title": st["title"], "status": "pending", "created": store.now().isoformat(timespec="seconds")}]
    JOBS.write_text(json.dumps(jl, ensure_ascii=False, indent=2), encoding="utf-8")
    return (f"📝 {KINDS[kind]} 대본 '{st['title']}' (작가 {used}) → PC 대기열에 넣음\n"
            f"훅: {' / '.join(st['hook'])}\n" + "\n".join(f"{i + 1}. {s['ko']}" for i, s in enumerate(st["scenes"]))
            + "\n🖥 PC에서 run_local_jobs.bat 실행(또는 예약)하면 렌더 → 앱 '방금 만든 영상'")


def jobs():
    return json.loads(JOBS.read_text(encoding="utf-8")) if JOBS.exists() else []
