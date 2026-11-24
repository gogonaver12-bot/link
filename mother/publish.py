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


def channels():
    return [{"id": "youtube", "name": "유튜브 숏츠", "ready": google_ready(), "need": "구글 1회 연결"},
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
def _py(*args):
    r = subprocess.run([sys.executable, *args], cwd=SHORTS, capture_output=True, text=True, timeout=900)
    return (r.stdout + r.stderr).strip()[-1500:]


def shorts(n=None, private=False):
    """대본 생성(성과 반영) → 훅 점수 검사 → 영상 렌더 → 업로드 → 성과 수집."""
    n = n or _cfg().get("shorts_per_day", 1)
    if not shutil.which("ffmpeg"):
        return "ffmpeg 없음 → 숏츠 건너뜀"
    log = []
    if google_ready():
        log.append(_py("upload.py", "--stats"))
    log.append(_py("feedback.py", "--n", str(n)))
    from .skillscore import hook_score
    done = store.load_json("published.json", {"blog": []})
    done.setdefault("shorts", [])
    made = 0
    for s in sorted((SHORTS / "scripts").glob("*.json")):
        if s.stem in done["shorts"]:
            continue
        meta = json.loads(s.read_text(encoding="utf-8"))
        score = (hook_score(meta.get("hook", "")) or {}).get("verdict", 0)
        need = _cfg().get("min_hook_score", 50)
        if score < need:  # 약한 훅 → AI가 채점 피드백대로 다시 써서 기준을 넘기면 진행
            new, new_score = improve_hook(meta, need)
            if new_score >= need:
                log.append(f"{s.name}: 훅 {score}→{new_score}점으로 개선")
                meta["hook"], score = new, new_score
                s.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                log.append(f"{s.name}: 훅 {score}점(개선 후 최고 {new_score}점) → 보류")
                continue
        log.append(_py("make_short.py", str(s)))
        mp4 = SHORTS / "out" / f"{s.stem}.mp4"
        if mp4.exists() and google_ready():
            args = ["upload.py", str(mp4)] + (["--private"] if private or _cfg().get("youtube_privacy", "public") != "public" else [])
            log.append(_py(*args))
        if mp4.exists():
            done["shorts"].append(s.stem)
            store.save_json("published.json", done)
        made += 1
        if made >= n:
            break
    return "\n".join(x for x in log if x)


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
