"""자동 업로드(공식 API만): 유튜브 숏츠 · 블로그(Blogger). 구글 1회 연결 후 사람 손 없이 매일 실행.

크몽·Gumroad 등 상품 자동 등록 API가 없는 곳은 '업로드 키트'(PDF+판매페이지)만 준비한다(약관상 봇 로그인 금지).
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys

from . import providers, store

SHORTS = store.ROOT / "shorts_factory"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/blogger"]


def google_ready():
    return all(os.getenv(k) for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "GOOGLE_OAUTH_REFRESH_TOKEN"))


def youtube_ready():  # 새 채널(F ai-LAB) 전용 토큰이 있으면 그 채널로 업로드
    return bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID") and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
                and (os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN") or os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")))


def channels():
    yt = "새 채널" if os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN") else "기존 계정 채널"
    st = store.cfg().get("story", {}).get("channel_name", "스토리 채널")
    return [{"id": "youtube", "name": f"유튜브 숏츠 ({yt})", "ready": youtube_ready(), "need": "구글 1회 연결"},
            {"id": "youtube_story", "name": f"유튜브 AI 실사 드라마 ({st})", "ready": bool(os.getenv("YOUTUBE_STORY_REFRESH_TOKEN")),
             "need": "스토리 채널 만들고 google_login_story.bat 실행 (그전엔 비공개로 올림)"},
            {"id": "blogger", "name": "블로그(Blogger)", "ready": google_ready() and bool(os.getenv("BLOGGER_BLOG_ID")),
             "need": "구글 1회 연결 + BLOGGER_BLOG_ID"},
            {"id": "kmong", "name": "크몽·Gumroad", "ready": False, "need": "자동 등록 API 없음 → 업로드 키트 준비"}]


def creds():
    from google.oauth2.credentials import Credentials
    return Credentials(None, refresh_token=os.environ["GOOGLE_OAUTH_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                       client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"], client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"], scopes=SCOPES)


def _cfg():
    return store.cfg().get("autopilot", {})


# ───────────────────────── 유튜브 숏츠 ─────────────────────────
def _py(*args, extra=None):
    sc = store.cfg().get("shorts", {})
    env = {**os.environ, "AI_IMAGES": "1" if sc.get("ai_images", True) else "0",
           "AI_VIDEO": "1" if sc.get("ai_video", True) else "0", "AI_VIDEO_BUDGET": str(sc.get("ai_video_budget_usd_month", 5)),
           "AI_VIDEO_PROVIDER": sc.get("ai_video_provider", "gemini"), "CHANNEL_NAME": sc.get("channel_name", ""),
           "STORY_CHANNEL_NAME": store.cfg().get("story", {}).get("channel_name", ""), **(extra or {})}
    r = subprocess.run([sys.executable, *args], cwd=SHORTS, capture_output=True, text=True, timeout=900, env=env)
    return (r.stdout + r.stderr).strip()[-1500:]


_limit = {"hit": False}
PREVIEWS = SHORTS.parent / "app" / "previews"


def preview(mp4, meta, keep=4):
    """앱 '영상확인'에서 바로 볼 미리보기(540p, 폰 화면에서 선명) — 최근 몇 개만 남김. 업로드 전·한도 초과여도 폰에서 확인 가능."""
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    out = PREVIEWS / mp4.name
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", "scale=540:-2:flags=lanczos", "-c:v", "libx264", "-crf", "26",
                        "-preset", "slow", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)], capture_output=True)
    if r.returncode:
        return None
    idx = store.load_json("previews.json", [])
    idx = [x for x in idx if x["file"] != out.name] + [{"file": out.name, "title": meta.get("title", ""), "date": store.today()}]
    for old in idx[:-keep]:
        (PREVIEWS / old["file"]).unlink(missing_ok=True)
    store.save_json("previews.json", idx[-keep:])
    return out


def produce(s, private, log, done):
    """대본 1개 → 훅 검사·개선 → 표지 문구 → 렌더 → 업로드 → 기록. 업로드 True / 실패 False / 훅 미달 보류 None."""
    from .skillscore import hook_score
    meta = json.loads(s.read_text(encoding="utf-8"))
    score = (hook_score(meta.get("hook", "")) or {}).get("verdict", 0)
    need = _cfg().get("min_hook_score", 50)
    if score < need and not meta.get("story"):  # 약한 훅(스토리 대사는 그대로 둠) → AI가 채점 피드백대로 다시 써서 기준을 넘기면 진행
        new, new_score = improve_hook(meta, need)
        if new_score >= need:
            log.append(f"{s.name}: 훅 {score}→{new_score}점으로 개선")
            meta["hook"], score = new, new_score
            s.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            log.append(f"{s.name}: 훅 {score}점(개선 후 최고 {new_score}점) → 보류")
            return None
    if not meta.get("cover"):  # 표지 문구 5안 → 0토큰 채점으로 1안 선택
        meta["cover"] = cover_copy(meta)
        s.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        log.append(f"{s.name}: 표지 문구 → {meta['cover'].replace(chr(10), ' / ')}")
    log.append(_py("make_short.py", str(s)))
    mp4 = SHORTS / "out" / f"{s.stem}.mp4"
    uploaded = False
    if mp4.exists():
        preview(mp4, meta)
    if meta.get("story") and not os.getenv("YOUTUBE_STORY_REFRESH_TOKEN"):
        private = True  # 스토리는 별도 채널 — 그 채널 연결 전엔 비공개
    if mp4.exists() and youtube_ready() and not _limit["hit"]:
        args = ["upload.py", str(mp4)] + (["--private"] if private or _cfg().get("youtube_privacy", "public") != "public" else [])
        res = _py(*args)
        log.append(res[-400:] if "Traceback" in res else res)
        uploaded = "youtube.com/shorts/" in res
        _limit["hit"] = "업로드 한도 초과" in res  # 오늘은 더 올려도 실패 → 이번 실행의 남은 업로드는 건너뜀
    if uploaded or (mp4.exists() and not youtube_ready()):  # 업로드 실패한 건 다음에 다시 시도
        done["shorts"].append(s.stem)
        store.save_json("published.json", done)
    return uploaded


def skip(ids):
    """대기 대본 빼기(삭제 아님 — 파일은 그대로, 제작만 안 함)."""
    done = store.load_json("published.json", {"blog": []})
    sk = done.setdefault("skipped", [])
    ids = [i.strip() for i in ids.split(",") if i.strip()]
    sk += [i for i in ids if i not in sk and (SHORTS / "scripts" / f"{i}.json").exists()]
    store.save_json("published.json", done)
    return f"대기열에서 뺌: {', '.join(ids)}"


def shorts(n=None, private=False, topic=""):
    """대본 생성(성과 반영) → 훅 점수 검사 → 영상 렌더 → 업로드 → 성과 수집."""
    n = n or _cfg().get("shorts_per_day", 1)
    if not shutil.which("ffmpeg"):
        return "ffmpeg 없음 → 숏츠 건너뜀"
    log = []
    if not private and store.cfg().get("shorts", {}).get("hold_until_new_channel") and not os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN"):
        private = True  # 새 채널 연결 전엔 기존 채널에 공개로 올리지 않음
        log.append("🔒 새 채널(F ai-LAB) 연결 전 → 비공개로 업로드 (google_login_youtube.bat 실행하면 새 채널 공개)")
    if youtube_ready():
        log.append(_py("upload.py", "--stats"))
    log.append(_py("feedback.py", "--n", str(n), extra={"SHORTS_TOPIC": topic[:200]} if topic else None))
    from .skillscore import hook_score
    done = store.load_json("published.json", {"blog": []})
    done.setdefault("shorts", [])
    made = 0
    files = sorted((SHORTS / "scripts").glob("*.json"), reverse=True)  # 방금 쓴(최신 피드백·주제 반영) 대본부터
    files = sorted(f for f in files if f.name.startswith("story-")) + [f for f in files if not f.name.startswith("story-")]  # 스토리는 1화부터 순서대로
    for s in files:
        if s.stem in done["shorts"] or s.stem in done.get("skipped", []):
            continue
        if produce(s, private, log, done) is None:  # 훅 미달 보류 → 다음 대본
            continue
        made += 1
        if made >= n:
            break
    return "\n".join(x for x in log if x)


def cover_copy(meta):
    """표지 문구 작가: 2~4줄, 보면 얻는 것 분명히, 강조어 딱 하나 → 제목 검사 점수로 최고안."""
    from .skillscore import title_check
    prompt = (f"숏츠 대본:\n제목: {meta.get('title')}\n첫 문장: {meta.get('hook')}\n본문: {' / '.join(meta.get('lines', [])[:6])}\n\n"
              "너는 숏츠 표지 문구 작가다. 화면 위쪽에 계속 떠 있을 표지 문구 5안을 써라. 각 안은 2~3줄(줄바꿈은 ' / '), 줄당 12자 이내, "
              "보면 얻는 것을 분명하게, '나만 모르는·3가지·진짜 이유'처럼 실제 숫자를 쓴 강조어는 안마다 딱 하나, 과장·허위 금지. "
              "한 줄에 한 안씩만 출력.")
    try:
        text, _ = providers.complete(prompt, system="숏츠 표지 문구 카피라이터. 안만 출력.", agent="cover_copywriter")
    except Exception:
        return meta.get("title", "")
    best, best_sc = meta.get("title", ""), -1
    for line in text.splitlines():
        cand = re.sub(r"^[\s\d.\-•*)안:]+", "", line).strip().strip('"')
        if not cand:
            continue
        flat = cand.replace(" / ", " ")
        if re.search(r"(?<![A-Za-z])N\s?(가지|개|배)", flat):  # 예시의 'N가지'를 그대로 베낀 안은 제외
            continue
        sc = (title_check(flat)["score"] - (20 if len(cand.split(" / ")) > 4 else 0)
              - (15 if len(re.findall(r"\d+", flat)) > 1 else 0)   # 숫자 강조는 안마다 하나만
              - (10 if re.search(r"\d+\s?배", flat) else 0))        # '2배' 같은 검증 안 되는 과장 감점
        if sc > best_sc:
            best, best_sc = cand, sc
    return best.replace(" / ", "\n")


def improve_hook(meta, need=50, rounds=3):
    """채점기(skillscore)의 약점·고칠 점을 AI에게 주고 훅 후보를 받아 0토큰 채점 → 최고점 선택."""
    from .skillscore import hook_score
    best, best_score = meta.get("hook", ""), (hook_score(meta.get("hook", "")) or {}).get("verdict", 0)
    for _ in range(rounds):
        h = hook_score(best) or {}
        prompt = (f"숏츠 주제: {meta.get('title')}\n본문: {' / '.join(meta.get('lines', [])[:4])}\n"
                  f"현재 첫 문장: {best} (점수 {h.get('verdict')}, 약점: {h.get('weakest')} → {h.get('fix')})\n\n"
                  "3초 안에 끝나는 첫 문장 후보 6개를 한 줄에 하나씩만 써라. 조건: 6~18어절, 구체적 숫자 1개 이상, "
                  "시청자에게 직접 말 걸기(여러분/~하시나요), 모르면 잃는 것(손해), 왜/어떻게 궁금증, 물음표로 끝. "
                  "과장·허위 금지, 내용과 맞게.")
        try:
            text, _ = providers.complete(prompt, system="숏츠 훅 카피라이터. 후보만 출력.", agent="hook_writer")
        except Exception:
            break
        for line in text.splitlines():
            cand = re.sub(r"^[\s\d.\-•*)]+", "", line).strip().strip('"')
            sc = (hook_score(cand) or {}).get("verdict", 0) if cand else 0
            if sc > best_score:
                best, best_score = cand, sc
        if best_score >= need:
            break
    return best, best_score


# ───────────────────────── 블로그 ─────────────────────────
def md_to_html(md):
    out, in_list = [], False
    for line in md.splitlines():
        t = html.escape(line.strip())
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        if line.strip().startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{t[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        m = re.match(r"^(#{1,4})\s+(.*)", t)
        if m:
            lv = min(4, len(m.group(1)) + 1)
            out.append(f"<h{lv}>{m.group(2)}</h{lv}>")
        elif t and not re.match(r"^\|?[\s:|-]+\|?$", t):
            out.append(f"<p>{t}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def blog(n=None):
    """하루 n편: 만든 상품의 한 장을 블로그용 글로 다시 쓰거나, 오늘 트렌드로 정보 글 작성 → Blogger 게시."""
    n = n or _cfg().get("blog_posts_per_day", 1)
    done = store.load_json("published.json", {"blog": []})
    done.setdefault("blog", [])
    out = []
    for _ in range(n):
        src = None
        for f in sorted((store.WORKSPACE / "products").glob("*/[0-9][0-9]-*.md")):
            if not f.name.startswith("00-") and str(f) not in done["blog"]:
                src = f
                break
        if src:
            base = src.read_text(encoding="utf-8")[:6000]
            prompt = ("아래 전자책 한 장을 검색에 잘 걸리는 블로그 글로 다시 써라: 질문형 제목 1줄(맨 위 '# 제목'), 핵심 요약, "
                      "본문은 원문의 절반 분량, 마지막에 '전체 가이드는 프로필 링크에서' 한 줄. 과장·허위 금지. 마크다운.\n\n" + base)
            key = str(src)
        else:
            from . import collector
            prompt = ("오늘 트렌드 중 1인 사업자에게 유용한 주제 하나를 골라 정보성 블로그 글을 써라: '# 제목' 한 줄, 핵심 요약, 본문 1,500자, "
                      "출처 링크 포함, 과장·허위 금지. 마크다운.\n\n" + collector.search(limit=12))
            key = f"trend-{store.today()}-{len(done['blog'])}"
        text, used = providers.complete(prompt, system="너는 SEO에 강한 블로그 작가다.", agent="blogger")
        title = (re.search(r"^#\s+(.+)$", text, re.M) or re.search(r"(.+)", text)).group(1).strip()[:120]
        body = re.sub(r"^#\s+.+$", "", text, count=1, flags=re.M)
        dest = store.WORKSPACE / "blog"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / f"{store.today()}-{len(done['blog']):03d}.md").write_text(text, encoding="utf-8")
        url = None
        if google_ready() and os.getenv("BLOGGER_BLOG_ID"):
            from googleapiclient.discovery import build
            api = build("blogger", "v3", credentials=creds(), cache_discovery=False)
            r = api.posts().insert(blogId=os.environ["BLOGGER_BLOG_ID"], isDraft=_cfg().get("blog_draft", False),
                                   body={"title": title, "content": md_to_html(body), "labels": ["AI", "부업"]}).execute()
            url = r.get("url")
            if url:
                done.setdefault("blog_posted", []).append({"date": store.today(), "title": title, "url": url})
        done["blog"].append(key)
        out.append(f"📝 {title} — " + (url or "글만 저장(구글 연결 시 자동 게시)") + f" · {used}")
    store.save_json("published.json", done)
    return "\n".join(out)


def kit(idea_id):
    """API 없는 판매처용: PDF·판매페이지 경로 안내."""
    d = f"workspace/products/{idea_id}"
    return f"업로드 키트: {d}/product.pdf + {d}/판매페이지.md"
