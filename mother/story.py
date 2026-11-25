"""AI 실사 스토리 영상: 시리즈 바이블(인물·세계관) → 인물 참조 사진 → 회차 대본 → 장면마다 같은 인물로 실사 이미지
→ 인물별 목소리 · 자막 · 음악 → 숏츠 업로드. 대본 작가는 Fable(Claude, 없으면 무료 AI), 그림은 Gemini.

stories/<slug>/bible.json · chars/<id>.jpg(참조 사진, 회차가 바뀌어도 같은 얼굴) · ep01.json …
"""
import json
import re
import zlib
import subprocess
import sys

from . import providers, store

DIR = store.ROOT / "stories"
SHORTS = store.ROOT / "shorts_factory"
VOICES = {  # edge-tts 목소리|음높이|속도
    "narrator": "ko-KR-HyunsuMultilingualNeural|+0Hz|+4%",
    "female": "ko-KR-SunHiNeural|+0Hz|+8%", "girl": "ko-KR-SunHiNeural|+30Hz|+10%",
    "male": "ko-KR-InJoonNeural|+0Hz|+5%", "boy": "ko-KR-InJoonNeural|+35Hz|+10%",
    "old_male": "ko-KR-InJoonNeural|-20Hz|-6%", "old_female": "ko-KR-SunHiNeural|-15Hz|-6%",
}
STYLE = ("photorealistic live-action film still, cinematic lighting, 35mm lens, shallow depth of field, realistic skin texture, "
         "vertical 9:16 composition with the subject in the upper two-thirds, no text, no letters, no watermark")
RULES = ("규칙: 오리지널 캐릭터만 — 기존 작품·캐릭터의 이름·외모·설정을 쓰지 않는다(공공 영역 전설·신화는 가능, "
         "SCP 재단 소재는 CC BY-SA 출처 표기). 실존 인물·혐오·선정적 묘사 금지. 대사는 짧고 자연스러운 한국어.")


def _cfg():
    return {"writer": store.cfg().get("shorts", {}).get("writer", "auto"), "images_per_episode": 12, **store.cfg().get("story", {})}


def _json(prompt, agent):
    try:
        text, used = providers.complete(prompt, system="너는 조회수 높은 AI 실사 숏드라마 작가다. JSON만 출력한다.", agent=agent,
                                        spec={"tier": "worker", "tools": [], "model": _cfg()["writer"]})
    except Exception:
        text, used = providers.complete(prompt, system="JSON만 출력한다.", agent=agent)
    return json.loads(text[text.index("{"): text.rindex("}") + 1]), used


def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s[:30] or f"s{store.today().replace('-', '')}"


def load(slug):
    return json.loads((DIR / slug / "bible.json").read_text(encoding="utf-8"))


def save(b):
    (DIR / b["slug"]).mkdir(parents=True, exist_ok=True)
    (DIR / b["slug"] / "bible.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")


def all_series():
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(DIR.glob("*/bible.json"))] if DIR.exists() else []


def _img():
    sys.path.insert(0, str(SHORTS))
    import aiimage
    return aiimage


def _jpg(png, out, width=640):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(png), "-vf", f"scale={width}:-2", "-q:v", "4", str(out)], check=True)
    return out


def new_series(logline, genre=""):
    bible, used = _json(
        f"로그라인: {logline}\n장르: {genre or '알아서'}\n\n이 로그라인으로 세로 숏드라마 시리즈 바이블을 JSON으로: "
        '{"title":"한국어 제목","title_en":"english slug words","genre":"","logline":"","tone":"",'
        '"setting":"영어: 시대·장소·분위기를 그림으로 그릴 수 있게","characters":[{"id":"영문 소문자 한 단어","name":"한국어 이름",'
        '"role":"","voice":"female|girl|male|boy|old_male|old_female","look":"영어: 나이·얼굴·머리·눈·체형·의상·특징을 구체적으로(매 장면 똑같이 그릴 수 있게)"}],'
        '"episodes":["1화 한 줄 요약","2화",...5개]}. 인물 2~4명. ' + RULES, "story_writer")
    bible["slug"] = slugify(bible.get("title_en") or bible.get("title", ""))
    if (DIR / bible["slug"]).exists():
        bible["slug"] += "-" + store.today()[5:].replace("-", "")
    bible.update({"created": store.today(), "made": [], "writer": used})
    save(bible)
    log = [f"📚 시리즈 '{bible['title']}' ({bible['slug']}) — 인물 {len(bible['characters'])}명 · 작가 {used}"]
    log += character_sheets(bible)
    return bible, log


def character_sheets(b):
    """인물마다 참조 사진 1장 — 이후 모든 장면에 같이 넣어 얼굴·옷이 바뀌지 않게."""
    out, ai = [], _img()
    d = DIR / b["slug"] / "chars"
    d.mkdir(parents=True, exist_ok=True)
    for c in b["characters"]:
        if (d / f"{c['id']}.jpg").exists():
            continue
        try:
            png = ai.generate(f"Character reference photo of {c['look']}. Full body and face clearly visible, standing, front view, "
                              f"plain neutral studio background, soft even light. Setting hint: {b.get('setting', '')}",
                              SHORTS / "assets" / "story" / b["slug"], style=STYLE, name=f"char-{c['id']}.png",
                              seed=zlib.crc32((b["slug"] + c["id"]).encode()) % 100000)
            if png:
                _jpg(png, d / f"{c['id']}.jpg")
                out.append(f"🧑 {c['name']} 참조 사진 완료")
        except Exception as e:
            out.append(f"⚠️ {c['name']} 참조 사진 실패({str(e)[:60]}) — Gemini 결제 연결이 필요할 수 있어요")
    return out


def _shot_prompt(b, shot):
    """장면 묘사의 [id] 를 인물 외모 설명으로 바꾸고, 등장 인물의 참조 사진을 고른다."""
    chars = {c["id"]: c for c in b["characters"]}
    ids = [i for i in chars if re.search(rf"\[{i}\]|\b{i}\b", shot)]
    text = re.sub(r"\[(\w+)\]", lambda m: f"{chars[m.group(1)]['name']} ({chars[m.group(1)]['look']})" if m.group(1) in chars else m.group(1), shot)
    refs = [DIR / b["slug"] / "chars" / f"{i}.jpg" for i in ids]
    return f"{text}. Setting: {b.get('setting', '')}", refs


def episode(slug, private=False):
    from .publish import produce
    b = load(slug)
    n = len(b["made"]) + 1
    prev = "\n".join(f"{m['n']}화: {m['summary']}" for m in b["made"][-4:]) or "없음(1화)"
    plan = b.get("episodes", [])
    ep, used = _json(
        f"시리즈 바이블:\n{json.dumps({k: b[k] for k in ('title', 'genre', 'logline', 'tone', 'setting', 'characters')}, ensure_ascii=False)}\n"
        f"지난 회차:\n{prev}\n이번 {n}화 계획: {plan[n - 1] if n <= len(plan) else '이야기를 자연스럽게 이어감'}\n\n"
        f"{n}화 대본 JSON: " '{"title":"","summary":"한 줄","scenes":[{"speaker":"narrator 또는 인물 id","line":"한국어 대사/내레이션 18자 안팎",'
        '"shot":"영어 장면 묘사: 등장 인물은 [id]로 표기, 행동·장소·카메라(close-up/medium/wide)·조명·표정"}],"cta":"다음 화가 궁금하게 + 구독",'
        '"description":"","tags":[""]}. 장면 8~11개(합쳐 50초 이내), 첫 장면은 3초 안에 궁금증, 마지막은 반전·떡밥. ' + RULES, "story_writer")
    scenes = [s for s in ep.get("scenes", []) if s.get("line")][:12]
    ai, imgs, log = _img(), [], [f"🎬 {b['title']} {n}화 '{ep.get('title', '')}' — 장면 {len(scenes)}개 · 작가 {used}"]
    cache = SHORTS / "assets" / "story" / slug
    fails = 0
    for i, sc in enumerate(scenes[:_cfg()["images_per_episode"]]):
        prompt, refs = _shot_prompt(b, sc.get("shot", ""))
        try:
            p = ai.generate(prompt, cache, refs=refs, style=STYLE, name=f"ep{n:02d}-{i:02d}.png",
                            seed=zlib.crc32(slug.encode()) % 100000 + i) if fails < 2 else None
        except Exception as e:
            p, fails = None, fails + 1
            if fails == 2:
                log.append(f"⚠️ 장면 이미지 실패({str(e)[:50]}) → 남은 장면은 무료 영상으로")
        imgs.append(str(p.relative_to(SHORTS)) if p else "")
    voice = lambda spk: VOICES["narrator"] if spk == "narrator" else VOICES.get(
        next((c.get("voice") for c in b["characters"] if c["id"] == spk), "female"), VOICES["female"])
    names = {c["id"]: c["name"] for c in b["characters"]}
    attrib = "\n\n출처: SCP 재단(SCP Foundation) — CC BY-SA 3.0" if "scp" in (b.get("genre", "") + b.get("logline", "")).lower() else ""
    script = {
        "title": f"{b['title']} {n}화 | {ep.get('title', '')}"[:90], "story": True,
        "hook": scenes[0]["line"], "lines": [s["line"] for s in scenes[1:]], "cta": ep.get("cta", ""),
        "voices": [voice(s.get("speaker")) for s in scenes] + [VOICES["narrator"]],
        "speakers": [names.get(s.get("speaker"), "") for s in scenes] + [""],
        "clips": imgs + [imgs[-1] if imgs else ""],
        "keywords": [" ".join(re.sub(r"\[\w+\]", "person", s.get("shot", "cinematic")).split()[:5]) for s in scenes] + ["cinematic"],
        "cover": f"{b['title']}\n{n}화", "colors": ["0x0b0b12", "0x2a1f3d"],
        "description": f"{ep.get('description', '')}\n\nAI로 만든 오리지널 숏드라마 (실존 인물 아님){attrib}",
        "tags": ep.get("tags", []) + ["AI드라마", "숏드라마", "AI실사화"],
    }
    sp = SHORTS / "scripts" / f"story-{slug}-ep{n:02d}.json"
    sp.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIR / slug / f"ep{n:02d}.json").write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    log.append(f"🖼 장면 이미지 {sum(1 for x in imgs if x)}/{len(scenes)}장 (나머지는 무료 영상)")
    done = store.load_json("published.json", {"blog": []})
    done.setdefault("shorts", [])
    sc = store.cfg().get("shorts", {})
    import os
    if not private and sc.get("hold_until_new_channel") and not os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN"):
        private = True
        log.append("🔒 새 채널 연결 전 → 비공개 업로드")
    ok = produce(sp, private, log, done)
    b["made"].append({"n": n, "title": ep.get("title", ""), "summary": ep.get("summary", ""), "date": store.today(),
                      "file": sp.stem, "uploaded": bool(ok)})
    save(b)
    return "\n".join(x for x in log if x)
