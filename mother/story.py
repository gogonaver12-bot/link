"""AI 실사 스토리 영상: 시리즈 바이블(인물·세계관) → 인물 참조 사진 → 회차 대본 → 장면마다 같은 인물로 실사 이미지
→ 인물별 목소리 · 자막 · 음악 → 숏츠 업로드. 대본 작가는 Fable(Claude, 없으면 무료 AI), 그림은 Gemini.

stories/<slug>/bible.json · chars/<id>.jpg(참조 사진, 회차가 바뀌어도 같은 얼굴) · ep01.json …
"""
import json
import re
import zlib
import subprocess
import sys

from . import cinematic, providers, store

DIR = store.ROOT / "stories"
SHORTS = store.ROOT / "shorts_factory"
VOICES = {  # edge-tts 목소리|음높이|속도
    "narrator": "ko-KR-HyunsuMultilingualNeural|+0Hz|+4%",
    "female": "ko-KR-SunHiNeural|+0Hz|+8%", "girl": "ko-KR-SunHiNeural|+30Hz|+10%",
    "male": "ko-KR-InJoonNeural|+0Hz|+5%", "boy": "ko-KR-InJoonNeural|+35Hz|+10%",
    "old_male": "ko-KR-InJoonNeural|-20Hz|-6%", "old_female": "ko-KR-SunHiNeural|-15Hz|-6%",
}
STYLE = ("photorealistic live-action K-drama film still, cinematic lighting with soft key light "
         "and rim light, sharp focus on the eyes, natural color grading, "
         "vertical 9:16 composition with the subject in the upper two-thirds, no text, no letters, no watermark, no cartoon, no 3d render")
RULES = ("규칙: 오리지널 캐릭터만 — 기존 작품·캐릭터의 이름·외모·설정을 쓰지 않는다(공공 영역 전설·신화는 가능, "
         "SCP 재단 소재는 CC BY-SA 출처 표기). 실존 인물·혐오·선정적 묘사 금지. 대사는 짧고 자연스러운 한국어.")


def _cfg():
    return {"writer": store.cfg().get("shorts", {}).get("writer", "auto"), "images_per_episode": 12, "motion_scenes": 4,
            "talk_scenes": 6, "subtitles": False,
            **store.cfg().get("story", {})}


def parse(text):
    """AI가 준 JSON을 너그럽게 읽기: 앞뒤 설명·끝 쉼표·둥근 따옴표·주석 정리."""
    t = text[text.index("{"): text.rindex("}") + 1]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        t = t.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
        t = re.sub(r"//[^\n\"]*\n", "\n", t)
        t = re.sub(r",\s*\.\.\.\s*", "", t)          # "...", 같은 생략 표시
        t = re.sub(r",\s*([}\]])", r"\1", t)            # 끝 쉼표
        return json.loads(t, strict=False)


def _json(prompt, agent):
    """1순위 Fable(설정된 작가) 자유 출력 → 형식이 깨지면 무료 AI 'JSON 모드'(형식 보장)로 다시 받음."""
    try:
        text, used = providers.complete(prompt, system="너는 조회수 높은 AI 실사 숏드라마 작가다. JSON만 출력한다.", agent=agent,
                                        spec={"tier": "worker", "tools": [], "model": _cfg()["writer"]})
        return parse(text), used
    except Exception as e:
        first = e
    try:
        return providers.json_complete("너는 조회수 높은 AI 실사 숏드라마 작가다.", prompt, {"type": "object"}, agent=agent + "_json"), "무료 AI(JSON 모드)"
    except Exception as e:
        raise RuntimeError(f"대본을 받지 못함: {str(first)[:80]} / {str(e)[:80]}")


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
        '"episodes":["1화 한 줄 요약","2화 한 줄 요약","3화 한 줄 요약","4화 한 줄 요약","5화 한 줄 요약"]}. 인물 2~4명. ' + RULES, "story_writer")
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


def talk_portraits(b):
    """인물마다 '대사용 얼굴 사진' 1장(가슴 위 정면, 시리즈 배경) — 말하는 장면은 늘 이 사진으로 만들어 회차가 바뀌어도 같은 얼굴."""
    out, ai = [], _img()
    d = DIR / b["slug"] / "chars"
    d.mkdir(parents=True, exist_ok=True)
    for c in b["characters"]:
        f = d / f"{c['id']}-talk.jpg"
        if f.exists():
            continue
        try:
            png = ai.generate(f"Medium close-up portrait of {c['look']}, facing the camera, face and mouth clearly visible, natural expression, "
                              f"in this place: {b.get('setting', '')}", SHORTS / "assets" / "story" / b["slug"], style=STYLE,
                              refs=[d / f"{c['id']}.jpg"], name=f"talk-{c['id']}.png", seed=zlib.crc32((b["slug"] + c["id"]).encode()) % 100000)
            if png:
                _jpg(png, f, width=720)
                out.append(f"🗣️ {c['name']} 대사용 얼굴 사진 완료")
        except Exception:
            pass
    return out


def _shot_prompt(b, shot):
    """장면 묘사의 [id] 를 인물 외모 설명으로 바꾸고, 등장 인물의 참조 사진을 고른다."""
    chars = {c["id"]: c for c in b["characters"]}
    ids = [i for i in chars if re.search(rf"\[{i}\]|\b{i}\b", shot)]
    clean = lambda t: re.sub(r"\b(English|영어)\s*:\s*", "", t)  # AI가 붙인 'English:' 머리말 제거
    text = re.sub(r"\[(\w+)\]", lambda m: f"{chars[m.group(1)]['name']} ({clean(chars[m.group(1)]['look'])})" if m.group(1) in chars else m.group(1),
                  clean(shot))
    refs = [DIR / b["slug"] / "chars" / f"{i}.jpg" for i in ids]
    return cinematic.compose(text, b.get("setting", "")), refs  # 5단계 황금 공식 순서(샷·무빙→피사체·동작→배경→조명→렌즈)


def _owner_rules():
    from .vfeedback import rules_text
    r = rules_text()
    return f"\n[사장님 피드백으로 정한 제작 규칙 — 반드시 지킬 것]\n{r}" if r else ""


def _write(b, n):
    prev = "\n".join(f"{m['n']}화: {m['summary']}" for m in b["made"][-4:]) or "없음(1화)"
    plan = b.get("episodes", [])
    return _json(
        f"시리즈 바이블:\n{json.dumps({k: b[k] for k in ('title', 'genre', 'logline', 'tone', 'setting', 'characters')}, ensure_ascii=False)}\n"
        f"지난 회차:\n{prev}\n이번 {n}화 계획: {plan[n - 1] if n <= len(plan) else '이야기를 자연스럽게 이어감'}\n\n"
        f"{n}화 대본 JSON: " '{"title":"","summary":"한 줄","scenes":[{"speaker":"narrator 또는 인물 id","line":"한국어 대사/내레이션 18자 안팎",'
        '"shot":"영어 장면 묘사(등장 인물은 [id]로 표기)"}],"cta":"다음 화가 궁금하게 + 구독",'
        '"description":"","tags":[""]}. 장면 8~11개(합쳐 50초 이내), 첫 장면은 3초 안에 궁금증, 마지막은 반전·떡밥. '
        + cinematic.WRITER_RULE + " " + RULES
        + _owner_rules(), "story_writer")


def _veo_prompt(b, sc, speak=None):
    """Google Flow·Gemini 앱(Veo)에 붙여넣을 장면 프롬프트 — 인물 사진을 재료(Ingredients)로 넣으면 같은 얼굴로 나옴.
    speak=True(인물 대사 장면): 그 인물이 한국어 대사를 직접 말하게(입 모양·목소리 포함)."""
    text, refs = _shot_prompt(b, sc.get("shot", ""))
    who = next((f"{c['name']} ({c['look'].split(',')[0]})" for c in b["characters"] if c["id"] == sc.get("speaker")), "")
    speak = (sc.get("speaker") not in (None, "", "narrator")) if speak is None else speak
    talk = (f'{who} looks at the other person and says in Korean, clearly with natural lip sync: "{sc.get("line", "")}" — then pauses. '
            "Only this one line of speech, natural room tone, no music." if speak else
            f'Mood matches this narration: "{sc.get("line", "")}". No speech, no music.')
    return (f"Vertical 9:16 live-action K-drama shot, 8 seconds, one clear action. {text}. Natural breathing and blinking. "
            f"{talk} Keep every person exactly like the attached reference photos. "
            "No subtitles, no on-screen text."), refs


def plan_episode(slug):
    """다음 화 대본 + 장면별 Gemini 프롬프트를 먼저 만들어 둠 → 폰 Gemini 앱으로 장면 영상을 만들어 올림 → story render."""
    b = load(slug)
    n = len(b["made"]) + 1
    ep, used = _write(b, n)
    scenes = [s for s in ep.get("scenes", []) if s.get("line")][:12]
    out = []
    for i, sc in enumerate(scenes):
        prompt, refs = _veo_prompt(b, sc)
        face = DIR / slug / "chars" / f"{sc.get('speaker')}-talk.jpg"
        refs = ([face] if face.exists() else []) + [r for r in refs if r != face]
        out.append({"i": i, "speaker": sc.get("speaker"), "line": sc["line"], "prompt": prompt,
                    "refs": [str(r.relative_to(store.ROOT)) for r in refs if r.exists()]})
    ep["scenes"] = scenes
    plan = {"n": n, "ep": ep, "writer": used, "created": store.today(), "scenes": out}
    (DIR / slug / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIR / slug / "clips").mkdir(parents=True, exist_ok=True)
    talk_portraits(b)
    return plan, (f"📝 {b['title']} {n}화 '{ep.get('title', '')}' 대본 준비 — 장면 {len(out)}개 · 앱에서 장면마다 Google Flow(또는 Gemini 앱)로 "
                  f"영상을 만들어 올린 뒤 '완성하기' (대사 장면은 인물이 직접 말하게 프롬프트에 대사 포함)")


def _has_audio(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def clip_path(slug, n, i):
    return DIR / slug / "clips" / f"ep{n:02d}-{i:02d}.mp4"


def render_episode(slug, private=False):
    """plan.json(없으면 새로 작성)으로 영상 완성: 올린 Gemini 장면 영상 우선 → 없으면 무료 그림(+앞 장면은 무료 영상 AI)."""
    from .publish import produce
    b = load(slug)
    pf = DIR / slug / "plan.json"
    plan = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else plan_episode(slug)[0]
    n, ep, used = plan["n"], plan["ep"], plan.get("writer", "")
    scenes = ep["scenes"]
    ai, imgs, log = _img(), [], [f"🎬 {b['title']} {n}화 '{ep.get('title', '')}' — 장면 {len(scenes)}개 · 작가 {used}"]
    log += character_sheets(b)  # 지난번에 못 만든 인물 사진이 있으면 이번에 만듦
    log += talk_portraits(b)
    cache = SHORTS / "assets" / "story" / slug
    fails, gem = 0, 0
    import os
    os.environ.setdefault("AI_VIDEO_BUDGET", str(store.cfg().get("shorts", {}).get("ai_video_budget_usd_month", 5)))  # Gemini 영상 월 예산
    voice = lambda spk: VOICES["narrator"] if spk == "narrator" else VOICES.get(
        next((c.get("voice") for c in b["characters"] if c["id"] == spk), "female"), VOICES["female"])
    sys.path.insert(0, str(SHORTS))
    import aivideo, hfvideo, hftalk
    audios, talks = [], 0
    for i, sc in enumerate(scenes[:_cfg()["images_per_episode"]]):
        # 대사 목소리를 먼저 만들어 둠 → 그 목소리로 '말하는 영상'을 만들고, 영상 합칠 때도 같은 파일을 써서 입 모양이 맞음
        au = cache / f"ep{n:02d}-{i:02d}.mp3"
        try:
            cache.mkdir(parents=True, exist_ok=True)
            if not au.exists():
                import make_short
                make_short.say(sc["line"], voice(sc.get("speaker")), "+12%", au)
            audios.append(str(au.relative_to(SHORTS)))
        except Exception:
            au = None
            audios.append("")
        speaks = sc.get("speaker") not in (None, "", "narrator") and au and talks < _cfg()["talk_scenes"]
        up = clip_path(slug, n, i)
        if up.exists():  # Google Flow·Gemini 앱으로 만들어 올린 장면 영상
            t = None
            if speaks and au:  # 인물이 그 영상 안에서 직접 말함 → 말 끝까지 잘라 그 소리를 이 줄 목소리로(입 모양과 같은 출처)
                try:
                    t = aivideo.speech_cut(up, au) if _has_audio(up) else None
                except Exception:
                    t = None
                t = t or hftalk.talk(None, au, cache / f"ep{n:02d}-{i:02d}-up-talk.mp4", motion=up)  # 소리 없는 영상이면 입 모양만 맞춤
            talks += bool(t)
            imgs.append(str(t.resolve()) if t else str(up.resolve()))
            gem += 1
            continue
        prompt, refs = _shot_prompt(b, sc.get("shot", ""))
        try:
            p = ai.generate(prompt, cache, refs=refs, style=STYLE, name=f"ep{n:02d}-{i:02d}.png",
                            seed=zlib.crc32(slug.encode()) % 100000 + i) if fails < 2 else None
        except Exception as e:
            p, fails = None, fails + 1
            if fails == 2:
                log.append(f"⚠️ 장면 이미지 실패({str(e)[:50]}) → 남은 장면은 무료 영상으로")
        still, motion = p, None
        if p and i < _cfg()["motion_scenes"] and not speaks:  # 내레이션·행동 장면: Gemini Veo(결제·예산 안) → 무료 영상 AI
            veo_prompt, _ = _veo_prompt(b, sc)
            motion = aivideo.veo_animate(p, veo_prompt, p.with_name(p.stem + "-veo.mp4")) or \
                hfvideo.animate(p, f"{sc.get('shot', '')}. {sc.get('line', '')}", p.with_suffix(".mp4"))
        if still and speaks:  # 인물 대사 장면: 대사용 얼굴 사진(회차 내내 같은 얼굴) + 목소리 → 말하며 움직이는 영상(입 모양 맞춤)
            face = DIR / slug / "chars" / f"{sc.get('speaker')}-talk.jpg"
            t = None
            vp, _ = _veo_prompt(b, sc)
            vv = aivideo.veo_animate(face if face.exists() else still, vp, still.with_name(still.stem + "-veo.mp4"))  # 프롬프트에 대사 포함
            if vv:  # Gemini Veo가 직접 말함 → 말 끝까지 잘라서 그 소리를 이 줄 목소리로 사용(입 모양과 소리가 같은 출처)
                try:
                    t = aivideo.speech_cut(vv, au)
                except Exception:
                    t = None
            t = t or hftalk.talk(face if face.exists() else still, au, still.with_name(still.stem + "-talk.mp4"))
            if t:
                motion, talks = t, talks + 1
            elif i < _cfg()["motion_scenes"]:
                motion = hfvideo.animate(p, f"{sc.get('shot', '')}. {sc.get('line', '')}", p.with_suffix(".mp4"))
        p = motion or still
        imgs.append(str(p.relative_to(SHORTS)) if p else "")
    names = {c["id"]: c["name"] for c in b["characters"]}
    attrib = "\n\n출처: SCP 재단(SCP Foundation) — CC BY-SA 3.0" if "scp" in (b.get("genre", "") + b.get("logline", "")).lower() else ""
    script = {
        "title": f"{b['title']} {n}화 | {ep.get('title', '')}"[:90], "story": True,
        "hook": scenes[0]["line"], "lines": [s["line"] for s in scenes[1:]], "cta": ep.get("cta", ""),
        "voices": [voice(s.get("speaker")) for s in scenes] + [VOICES["narrator"]],
        "speakers": [names.get(s.get("speaker"), "") for s in scenes] + [""],
        "clips": imgs + [imgs[-1] if imgs else ""],
        "audio": audios + [""],  # 줄마다 미리 만든 목소리(말하는 영상과 같은 파일)
        "no_subtitles": not _cfg()["subtitles"],  # 실사 스토리: 자막 없이 움직임과 말로
        "keywords": [" ".join(re.sub(r"\[\w+\]", "person", s.get("shot", "cinematic")).split()[:5]) for s in scenes] + ["cinematic"],
        "cover": f"{b['title']}\n{n}화", "colors": ["0x0b0b12", "0x2a1f3d"],
        "description": f"{ep.get('description', '')}\n\nAI로 만든 오리지널 숏드라마 (실존 인물 아님){attrib}",
        "tags": ep.get("tags", []) + ["AI드라마", "숏드라마", "AI실사화"],
        # 어린이용이면 유튜브에 '아동용'으로 신고 (법적 의무 · 댓글·맞춤광고 꺼짐)
        "made_for_kids": bool(re.search(r"어린이|동화|유아|키즈|kids|children", b.get("genre", "") + b.get("logline", ""), re.I)),
    }
    sp = SHORTS / "scripts" / f"story-{slug}-ep{n:02d}.json"
    sp.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (DIR / slug / f"ep{n:02d}.json").write_text(json.dumps(ep, ensure_ascii=False, indent=2), encoding="utf-8")
    veo = sum(1 for x in imgs if x.endswith("-veo.mp4"))
    tk = sum(1 for x in imgs if x.endswith("-talk.mp4"))
    log.append(f"🖼 장면 {len(scenes)}개: 🗣️ 말하는 영상 {tk} · 직접 올린 Gemini 영상 {gem} · Gemini Veo {veo} · 무료 움직임 "
               f"{sum(1 for x in imgs if x.endswith('.mp4')) - tk - veo - gem} · 사진 {sum(1 for x in imgs if x and not x.endswith('.mp4'))} · 자막 {'있음' if _cfg()['subtitles'] else '없음'}")
    done = store.load_json("published.json", {"blog": []})
    done.setdefault("shorts", [])
    sc = store.cfg().get("shorts", {})
    import os
    if not private and not os.getenv("YOUTUBE_STORY_REFRESH_TOKEN"):  # 스토리는 별도 채널 — 연결 전엔 공개로 올리지 않음
        private = True
        log.append("🔒 스토리 채널 연결 전 → 비공개 업로드 (google_login_story.bat 실행하면 그 채널에 공개)")
    ok = produce(sp, private, log, done)
    b["made"].append({"n": n, "title": ep.get("title", ""), "summary": ep.get("summary", ""), "date": store.today(),
                      "file": sp.stem, "uploaded": bool(ok)})
    save(b)
    pf.unlink(missing_ok=True)
    return "\n".join(x for x in log if x)


def episode(slug, private=False):
    """다음 화를 한 번에(대본 → 장면 → 영상 → 업로드)."""
    return render_episode(slug, private)
