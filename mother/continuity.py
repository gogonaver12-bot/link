"""AI 실사 드라마 스토리 일관성: Flow 캐릭터 이미지 우선 · 고정 외모 설명 · 연속성 장부 · 대본 일관성 검사.

stories/<slug>/chars/<id>.jpg (+ -talk·-smile·-side) — 앱에서 올린 Flow 이미지는 옆에 <같은 이름>.flow 표시 파일이 생김
bible.json 의 characters[].fixed — 나이·얼굴·머리·옷·소품·체형(한 번 정하면 바뀌지 않음, 모든 장면 프롬프트 앞에 똑같이)
stories/<slug>/continuity.json — 회차 요약·시간순 사건·인물 상태·장소·소품·떡밥 (회차마다 자동 갱신 → 다음 화 작가에게)
stories/<slug>/check.json — 마지막 일관성 점검 결과(앱 표시용)
"""
import json
import re

from . import providers, store

FIELDS = ("age", "face", "hair", "outfit", "props", "body")
KINDS = ("talk", "smile", "side")  # 선택 추가 사진: 대사용 얼굴·표정·옆모습
CHECKS = ("이름", "성격", "말투", "외모", "설정", "이전 사건")


def _dir(slug):
    from . import story
    return story.DIR / slug


def _clean(t):
    return re.sub(r"\b(English|영어)\s*:\s*", "", str(t or "")).strip()


# ───────── 1. Flow 캐릭터 이미지 ─────────
def is_flow(slug, cid, kind=""):
    """앱에서 Flow 이미지를 올렸는지 (<id>[-kind].flow 표시 파일)."""
    return (_dir(slug) / "chars" / f"{cid}{'-' + kind if kind else ''}.flow").exists()


def face(slug, cid):
    """대사용 얼굴: 직접 올린 -talk → (Flow 본 사진이 있으면) Flow 본 사진 → 자동 -talk → 자동 본 사진."""
    d = _dir(slug) / "chars"
    talk, main = d / f"{cid}-talk.jpg", d / f"{cid}.jpg"
    if is_flow(slug, cid, "talk") and talk.exists():
        return talk
    if is_flow(slug, cid) and main.exists():
        return main  # 자동 생성 대사 사진보다 Flow 원본 얼굴이 우선
    return talk if talk.exists() else main


def images(slug, cid):
    """캐릭터의 모든 참조 사진 [(kind, path, flow?)] — 본 사진 먼저."""
    d = _dir(slug) / "chars"
    out = []
    for k in ("",) + KINDS:
        p = d / f"{cid}{'-' + k if k else ''}.jpg"
        if p.exists():
            out.append((k or "main", p, is_flow(slug, cid, k)))
    return out


# ───────── 2. 고정 외모 설명 ─────────
def _split_look(look):
    """AI 없이도: 영어 외모 문장을 쉼표로 나눠 항목에 배치."""
    parts = [p.strip() for p in re.split(r",|;| and wearing | wearing ", _clean(look)) if p.strip()]
    f = dict.fromkeys(FIELDS, "")
    keys = {"age": r"\d+.?year|old|young|child|teen|adult|elderly|\bage", "hair": r"hair|bald|braid|ponytail|crew cut|bun",
            "outfit": r"wear|dress|tunic|shirt|coat|jacket|robe|uniform|armor|vest|boots|plates|hoodie|skirt|suit",
            "props": r"holding|carr|sword|bag|staff|glasses|necklace|ring|hat|scarf",
            "body": r"build|tall|short|slim|muscular|thin|stocky|petite|figure|height|float|hover",
            "face": r"face|eye|jaw|nose|freckle|beard|skin|cheek|lip|scar|mustache"}
    for p in parts:
        k = next((k for k, rx in keys.items() if re.search(rx, p, re.I)), "face")
        f[k] = f"{f[k]}, {p}".strip(", ")
    return f


def ensure_fixed(b):
    """캐릭터마다 바뀌지 않는 외모 설명(fixed)이 없으면 한 번만 정해 bible에 저장. 반환: 새로 정한 인물 수."""
    new = 0
    for c in b.get("characters", []):
        fx = c.get("fixed")
        if isinstance(fx, dict) and any(fx.get(k) for k in FIELDS):
            continue
        fx = None
        try:
            fx = providers.json_complete(
                "너는 드라마 의상·분장 실장이다. 영어로만 짧게 쓴다.",
                f"캐릭터 외모: {_clean(c.get('look'))}\n이 외모를 매 장면 똑같이 그릴 수 있게 항목별 영어 구절로 고정: "
                '{"age":"","face":"","hair":"","outfit":"","props":"없으면 none","body":""}. 원래 설명에 없는 건 그 인물에 맞게 하나로 정한다.',
                {"type": "object", "properties": {k: {"type": "string"} for k in FIELDS}}, agent="story_lock")
        except Exception:
            pass
        if not isinstance(fx, dict) or not any(str(fx.get(k, "")).strip() for k in FIELDS):
            fx = _split_look(c.get("look", ""))
        c["fixed"] = {k: _clean(fx.get(k, "")) for k in FIELDS}
        new += 1
    return new


def lock(c):
    """한 인물의 고정 외모 한 줄(영어) — 모든 장면에 글자 하나 안 바꾸고 똑같이 붙임."""
    fx = c.get("fixed") or _split_look(c.get("look", ""))
    body = "; ".join(fx[k] if fx[k].lower().startswith(k) else f"{k} {fx[k]}" for k in FIELDS if fx.get(k) and fx[k].lower() != "none")
    return f"{c['name']} [{c['id']}]: {body or _clean(c.get('look'))}"


def lock_block(b, ids):
    """장면 프롬프트 맨 앞 'CHARACTER LOCK' 블록(등장 인물만, 늘 같은 문장)."""
    cs = [c for c in b.get("characters", []) if c["id"] in ids]
    return ("CHARACTER LOCK (identical in every scene, never change face, hair, outfit, props or body): "
            + " | ".join(lock(c) for c in cs) + ". ") if cs else ""


def ingredients(b, ids):
    """Flow용 안내(한국어): 이 장면에 재료(Ingredients)로 넣을 캐릭터 이미지."""
    names = {c["id"]: c["name"] for c in b.get("characters", [])}
    have = [i for i in ids if i in names and (_dir(b["slug"]) / "chars" / f"{i}.jpg").exists()]
    if not have:
        return ""
    return ("🧩 Flow 재료(Ingredients)에 이 캐릭터 이미지를 넣으세요: "
            + ", ".join(f"{names[i]}({i}.jpg{' · Flow 원본' if is_flow(b['slug'], i) else ''})" for i in have))


# ───────── 3. 연속성 장부 ─────────
EMPTY = {"episodes": [], "timeline": [], "characters": {}, "locations": [], "props": [], "threads": []}


def load(slug):
    f = _dir(slug) / "continuity.json"
    try:
        return {**EMPTY, **json.loads(f.read_text(encoding="utf-8"))} if f.exists() else json.loads(json.dumps(EMPTY))
    except Exception:
        return json.loads(json.dumps(EMPTY))


def save(slug, led):
    _dir(slug).mkdir(parents=True, exist_ok=True)
    (_dir(slug) / "continuity.json").write_text(json.dumps(led, ensure_ascii=False, indent=2), encoding="utf-8")


def brief(slug, limit=1800):
    """다음 회차 작가에게 넘길 장부 요약(짧게)."""
    led = load(slug)
    if not led["episodes"]:
        return ""
    lines = ["[연속성 장부 — 반드시 이어서 쓸 것]"]
    lines += [f"{e.get('n')}화: {e.get('summary', '')}" for e in led["episodes"][-5:]]
    if led["timeline"]:
        lines.append("사건 순서: " + " → ".join(map(str, led["timeline"][-12:])))
    for cid, st in led["characters"].items():
        if isinstance(st, dict):
            s = ", ".join(f"{k} {v}" for k, v in st.items() if v)
            if s:
                lines.append(f"{cid} 상태: {s}")
    for k, lab in (("locations", "장소"), ("props", "중요 소품"), ("threads", "남은 떡밥(풀거나 이어갈 것)")):
        if led[k]:
            lines.append(f"{lab}: " + "; ".join(map(str, led[k][-8:])))
    return "\n".join(lines)[:limit]


def _merge(led, n, ep, new):
    led["episodes"] = [e for e in led["episodes"] if e.get("n") != n] + [{"n": n, "title": ep.get("title", ""),
                                                                         "summary": new.get("summary") or ep.get("summary", "")}]
    led["timeline"] += [f"{n}화: {e}" for e in (new.get("events") or [])][:8]
    for cid, st in (new.get("characters") or {}).items():
        if isinstance(st, dict):
            led["characters"].setdefault(cid, {}).update({k: v for k, v in st.items() if v})
    for k in ("locations", "props"):
        for x in new.get(k) or []:
            if x and x not in led[k]:
                led[k].append(x)
    done = set(new.get("resolved") or [])
    led["threads"] = [t for t in led["threads"] if t not in done] + [t for t in (new.get("threads") or []) if t and t not in led["threads"]]
    return led


def update(b, n, ep):
    """회차를 만든 뒤 장부 자동 갱신(무료 AI → 실패하면 대본에서 바로 뽑음)."""
    led = load(b["slug"])
    new = None
    try:
        new = providers.json_complete(
            "너는 드라마 스크립터(연속성 담당)다. 한국어로 짧게.",
            f"지금까지 장부:\n{json.dumps(led, ensure_ascii=False)[:3000]}\n\n이번 {n}화 대본:\n{json.dumps(ep, ensure_ascii=False)[:3500]}\n\n"
            "이번 화로 바뀐 것만 JSON: {\"summary\":\"한 줄\",\"events\":[\"시간순 사건\"],\"characters\":{\"인물id\":{\"injury\":\"부상(없으면 빈칸)\","
            "\"outfit\":\"옷 변화\",\"relations\":\"관계 변화\",\"state\":\"감정·처지\"}},\"locations\":[\"\"],\"props\":[\"중요 소품\"],"
            "\"threads\":[\"새 떡밥\"],\"resolved\":[\"이번에 풀린 기존 떡밥(장부 문장 그대로)\"]}",
            {"type": "object"}, agent="story_continuity")
    except Exception:
        pass
    if not isinstance(new, dict):
        scenes = ep.get("scenes", [])
        new = {"summary": ep.get("summary", ""), "events": [s["line"] for s in scenes if s.get("speaker") == "narrator"][:5],
               "threads": [scenes[-1]["line"]] if scenes else []}
    led = _merge(led, n, ep, new)
    led["updated"] = store.today()
    save(b["slug"], led)
    return led


# ───────── 4. 일관성 검사 ─────────
def _rule_issues(b, ep):
    """AI 없이 확실히 잡는 것: 없는 인물 id·이름 오기."""
    ids = {c["id"] for c in b.get("characters", [])}
    names = {c["name"]: c["id"] for c in b.get("characters", [])}
    out = []
    for i, s in enumerate(ep.get("scenes", [])):
        sp = s.get("speaker")
        if sp not in ids | {"narrator", None, ""}:
            fix = names.get(sp) or next((k for k in ids if str(sp).lower() == k), None)
            out.append({"type": "이름", "scene": i + 1, "detail": f"없는 인물 '{sp}' → {fix or 'narrator'}"})
            s["speaker"] = fix or "narrator"
        for m in set(re.findall(r"\[(\w+)\]", s.get("shot", ""))):
            if m not in ids:
                fix = names.get(m)
                out.append({"type": "이름", "scene": i + 1, "detail": f"장면의 [{m}] → {fix or '삭제'}"})
                s["shot"] = s["shot"].replace(f"[{m}]", f"[{fix}]" if fix else "a person")
    return out


def check(b, ep, rounds=2):
    """새 회차 대본을 설정집·장부와 맞춰 봄 → 어긋나면 AI가 고쳐 다시 씀. 반환: (고친 대본, 점검 결과)."""
    issues = _rule_issues(b, ep)
    bible = {k: b.get(k) for k in ("title", "genre", "tone", "setting")}
    bible["characters"] = [{k: c.get(k) for k in ("id", "name", "role", "voice", "look", "fixed", "speech", "personality")}
                           for c in b.get("characters", [])]
    led, used, rewrote = brief(b["slug"]), "규칙 검사", False
    for _ in range(rounds):
        try:
            r = providers.json_complete(
                "너는 드라마 일관성 검사관이다. 설정집과 연속성 장부를 기준으로 새 대본을 검사한다.",
                f"설정집:\n{json.dumps(bible, ensure_ascii=False)[:3000]}\n\n{led or '장부: 없음(1화)'}\n\n새 대본:\n{json.dumps(ep, ensure_ascii=False)[:4000]}\n\n"
                f"검사 항목: {', '.join(CHECKS)}. 어긋난 것만 issues에. 어긋나면 fixed에 같은 형식(title·summary·scenes·cta·description·tags)으로 "
                "고친 전체 대본(장면 수·shot의 [id] 표기 유지, 대사는 한국어). 문제 없으면 ok=true, fixed는 {}. "
                'JSON: {"ok":true,"issues":[{"type":"이름|성격|말투|외모|설정|이전 사건","scene":1,"detail":"한국어 한 줄"}],"fixed":{}}',
                {"type": "object"}, agent="story_check")
            used = "무료 AI"
        except Exception:
            break
        found = [x for x in (r.get("issues") or []) if isinstance(x, dict)]
        fx = r.get("fixed") if isinstance(r.get("fixed"), dict) else {}
        if r.get("ok") or not found:
            break
        issues += found
        if not (fx.get("scenes") and all(isinstance(s, dict) and s.get("line") for s in fx["scenes"])):
            break
        ep = {**ep, **fx}
        issues += _rule_issues(b, ep)
        rewrote = True
    report = {"date": store.today(), "by": used, "ok": not issues, "rewrote": rewrote, "items": list(CHECKS), "issues": issues[:20]}
    return ep, report


def save_check(slug, n, report):
    _dir(slug).mkdir(parents=True, exist_ok=True)
    (_dir(slug) / "check.json").write_text(json.dumps({"n": n, **report}, ensure_ascii=False, indent=2), encoding="utf-8")


def read_check(slug):
    f = _dir(slug) / "check.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    except Exception:
        return None
