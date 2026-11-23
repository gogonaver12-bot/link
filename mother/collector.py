"""정보 수집 (jarvis-ai-hub 계승): 공개 RSS/Atom만 모아 data/news.json 에 저장 — LLM 없이 0토큰.

- 외부 텍스트는 신뢰하지 않는다: 저장·표시만 하고 지시로 실행하지 않는다.
- 프롬프트 인젝션 의심 문장은 표시(flag)하고, 크롤링 결과에도 경고를 붙인다.
- 제목·링크·짧은 요약(300자)만 보관, 같은 글은 중복 제거.
"""
import hashlib
import html
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

import requests

from . import store

UA = "LinkMotherBot/1.0 (+personal research; respects robots and rate limits)"
DEFAULT_FEEDS = [  # (이름, URL, 분류) — config.yaml 의 feeds 로 덮어쓰기/추가 가능
    ("구글 트렌드 KR", "https://trends.google.com/trending/rss?geo=KR", "trend"),
    ("구글 트렌드 US", "https://trends.google.com/trending/rss?geo=US", "trend"),
    ("구글 트렌드 JP", "https://trends.google.com/trending/rss?geo=JP", "trend"),
    ("Hacker News", "https://hnrss.org/frontpage", "tech"),
    ("Product Hunt", "https://www.producthunt.com/feed", "product"),
    ("Anthropic SDK 릴리스", "https://github.com/anthropics/anthropic-sdk-python/releases.atom", "ai"),
    ("Google GenAI SDK 릴리스", "https://github.com/googleapis/python-genai/releases.atom", "ai"),
    ("Ollama 릴리스", "https://github.com/ollama/ollama/releases.atom", "ai"),
    ("GitHub 변경 로그", "https://github.blog/changelog/feed/", "devtools"),
]
INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|prompts)",
    r"disregard (the )?(system|previous) (prompt|instructions)",
    r"you are now (in )?(developer|dan|jailbreak)",
    r"reveal (your )?(system prompt|api key|secret)",
    r"(이전|위의|기존) (지시|명령|규칙)[을를]? (모두 )?무시",
    r"시스템 프롬프트[를을]? (출력|공개|보여)",
    r"curl [^|]+\|\s*(ba)?sh",
    r"powershell(\.exe)? .*-enc(odedcommand)?",
    r"rm -rf /",
    r"Invoke-Expression|iex\s*\(",
    r"send (me|us) (the|your) (api key|token|password)",
]
_INJ = [re.compile(p, re.I) for p in INJECTION_PATTERNS]
_TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref"}
MAX_ITEMS = 400


def detect_injection(text):
    return any(p.search(text or "") for p in _INJ)


def strip_html(text):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text or "", flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def normalize_url(url):
    p = urlsplit(url.strip())
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if k not in _TRACKING])
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), q, ""))


def parse_feed(xml_text):
    """RSS 2.0과 Atom을 모두 읽는다."""
    root = ET.fromstring(xml_text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    if root.tag.endswith("feed"):
        for e in root.findall("a:entry", ns):
            link = e.find("a:link[@rel='alternate']", ns)
            if link is None:
                link = e.find("a:link", ns)
            out.append({"title": (e.findtext("a:title", "", ns) or "").strip(),
                        "url": link.get("href", "") if link is not None else "",
                        "summary": e.findtext("a:summary", "", ns) or e.findtext("a:content", "", ns) or "",
                        "published": e.findtext("a:updated", "", ns) or e.findtext("a:published", "", ns)})
    else:
        for it in root.iter("item"):
            out.append({"title": (it.findtext("title") or "").strip(), "url": (it.findtext("link") or "").strip(),
                        "summary": it.findtext("description") or "", "published": it.findtext("pubDate") or ""})
    return out


# 자동 추가 후보: 나라별 사업·트렌드 사이트 (검증 통과한 것만 매일 조금씩 추가)
CANDIDATES = [
    ("구글 트렌드 TW", "https://trends.google.com/trending/rss?geo=TW", "trend"),
    ("구글 트렌드 GB", "https://trends.google.com/trending/rss?geo=GB", "trend"),
    ("구글 트렌드 VN", "https://trends.google.com/trending/rss?geo=VN", "trend"),
    ("플래텀", "https://platum.kr/feed", "business"),
    ("벤처스퀘어", "https://www.venturesquare.net/feed", "business"),
    ("전자신문", "https://rss.etnews.com/Section901.xml", "tech"),
    ("TechCrunch", "https://techcrunch.com/feed/", "business"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "tech"),
    ("ITmedia", "https://rss.itmedia.co.jp/rss/2.0/itmedia_all.xml", "tech"),
    ("GIGAZINE", "https://gigazine.net/news/rss_2.0/", "tech"),
    ("GitHub 트렌딩", "https://mshibanami.github.io/GitHubTrendingRSS/daily/all.xml", "ai"),
    ("Hugging Face 블로그", "https://huggingface.co/blog/feed.xml", "ai"),
    ("Shopify 블로그", "https://www.shopify.com/blog.atom", "business"),
    ("Etsy 판매자 소식", "https://www.etsy.com/seller-handbook/rss", "business"),
]
MAX_FAILS = 7  # 연속 실패 7회(약 일주일) → 자동 탈락


def _sources():
    src = store.load_json("sources.json", None)
    if src is None:  # 처음: 기본 출처 + config.yaml feeds 로 시작
        extra = [(f["name"], f["url"], f.get("category", "custom")) for f in store.cfg().get("feeds", [])]
        src = [{"name": n, "url": u, "category": c, "origin": "기본", "added": store.today(), "fails": 0, "ok": 0}
               for n, u, c in DEFAULT_FEEDS + extra if u.startswith("https://")]
        store.save_json("sources.json", src)
    return src


def feeds():
    return [(x["name"], x["url"], x["category"]) for x in _sources() if not x.get("removed")]


def _fetch_feed(url):
    r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    try:
        entries = parse_feed(r.content[:2_000_000])
        if entries:
            return url, entries
    except ET.ParseError:
        pass
    m = re.search(r'<link[^>]+type="application/(?:rss|atom)\+xml"[^>]*>', r.text[:200_000], re.I)  # 일반 사이트 → 피드 주소 찾기
    href = re.search(r'href="([^"]+)"', m.group(0)) if m else None
    if href:
        from urllib.parse import urljoin
        feed = urljoin(url, html.unescape(href.group(1)))
        if feed.startswith("https://") and feed != url:
            return _fetch_feed(feed)
    raise ValueError("RSS/Atom 피드 없음")


def add_source(url, name="", category="custom", origin="수동"):
    """사이트 추가: 일반 주소를 넣어도 피드를 찾아 검증 후 등록. 이미 있으면 건너뜀."""
    if not url.startswith("https://"):
        return "https 주소만 추가할 수 있어요"
    src = _sources()
    try:
        feed, entries = _fetch_feed(url)
    except Exception as e:
        return f"추가 실패({type(e).__name__}): 피드를 읽을 수 없는 사이트예요"
    if any(normalize_url(x["url"]) == normalize_url(feed) for x in src):
        return f"이미 있어요: {feed}"
    if detect_injection(" ".join(e["title"] for e in entries[:10])):
        return "추가 거부: AI 조작 시도 문장이 있는 사이트"
    name = name or urlsplit(feed).netloc.removeprefix("www.")
    src.append({"name": name[:40], "url": feed, "category": category, "origin": origin, "added": store.today(), "fails": 0, "ok": 0})
    store.save_json("sources.json", src)
    return f"추가됨: {name} ({len(entries)}개 글)"


DISCOVER_PROMPT = ("1인 온라인 사업(디지털 상품·콘텐츠·이커머스·AI 서비스)에 도움 되는 최신 트렌드/시장 정보를 주는 사이트의 "
                   "RSS 또는 Atom 피드 주소를 시장별({markets})로 찾아라. 이미 있는 사이트 제외: {have}. "
                   "확실히 존재하는 https 피드 주소만, 한 줄에 하나씩 URL만 출력. 최대 6개.")


def discover(max_new=3):
    """매일 새 출처 자동 추가: ① 후보 목록 ② 수집 글에 자주 나온 사이트 ③ 무료 AI 추천 → 검증 통과한 것만."""
    have = {urlsplit(x["url"]).netloc for x in _sources()}
    tried = set(store.load_json("sources_tried.json", []))
    added = []

    def attempt(url, name="", cat="custom", origin="자동"):
        if url in tried or urlsplit(url).netloc in have or len(added) >= max_new:
            return
        tried.add(url)
        res = add_source(url, name, cat, origin)
        if res.startswith("추가됨"):
            added.append(res.removeprefix("추가됨: "))
            have.add(urlsplit(url).netloc)

    for n, u, c in CANDIDATES:
        attempt(u, n, c, "후보목록")
    counts = {}
    for i in store.load_json("news.json", [])[-200:]:
        d = urlsplit(i.get("url", "")).netloc
        if d and d not in have and "google.com" not in d:
            counts[d] = counts.get(d, 0) + 1
    for d, n in sorted(counts.items(), key=lambda x: -x[1])[:5]:
        if n >= 2:
            attempt(f"https://{d}/", cat="tech", origin="자주 등장")
    if len(added) < max_new:
        try:
            from . import providers
            text, _ = providers.complete(DISCOVER_PROMPT.format(
                markets=", ".join(m["code"] for m in store.cfg()["markets"]), have=", ".join(sorted(have))[:800]),
                system="URL 목록만 출력한다.", agent="source_scout")
            for u in re.findall(r"https://[^\s<>\"')\]]+", text)[:6]:
                attempt(u.rstrip(".,"), cat="business", origin="AI 추천")
        except Exception:
            pass  # AI 없으면 후보·자동 발견만
    store.save_json("sources_tried.json", sorted(tried)[-500:])
    return added


def collect():
    items = store.load_json("news.json", [])
    seen = {i["id"] for i in items}
    added, failed = 0, []
    src = _sources()
    for x in src:
        if x.get("removed"):
            continue
        name, url, cat = x["name"], x["url"], x["category"]
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
            r.raise_for_status()
            entries = parse_feed(r.content[:2_000_000])
            x.update(fails=0, ok=x.get("ok", 0) + 1, last_ok=store.today())
        except Exception as e:  # 한 출처 실패는 건너뛰고 계속, 계속 실패하면 탈락
            failed.append(f"{name}: {type(e).__name__}")
            x["fails"] = x.get("fails", 0) + 1
            if x["fails"] >= MAX_FAILS:
                x["removed"] = store.today()
            continue
        for e in entries[:20]:
            title = strip_html(e["title"])[:200]
            if not title:
                continue
            h = hashlib.sha256((normalize_url(e["url"]) if e["url"] else title.lower()).encode()).hexdigest()[:16]
            if h in seen:
                continue
            summary = strip_html(e["summary"])[:300]
            link = e["url"]
            if "trends.google.com/trending/rss" in link or not link:  # 구글 트렌드는 검색어 검색 링크로
                link = "https://www.google.com/search?q=" + quote(title)
            seen.add(h)
            added += 1
            items.append({"id": h, "source": name, "category": cat, "title": title, "url": link,
                          "summary": summary, "published": e["published"], "collected": store.now().isoformat(timespec="minutes"),
                          "flag": detect_injection(f"{title} {summary}")})
    store.save_json("news.json", items[-MAX_ITEMS:])
    store.save_json("sources.json", src)
    return added, failed


def search(query="", category="", limit=15):
    q = query.lower()
    rows = [i for i in reversed(store.load_json("news.json", []))
            if (not q or q in (i["title"] + " " + i["summary"]).lower()) and (not category or i["category"] == category)]
    return "\n".join(("⚠️인젝션의심 " if i["flag"] else "") + f"- [{i['source']}] {i['title']} | {i['url']}" for i in rows[:limit]) \
        or "결과 없음 (먼저 python -m mother news 로 수집)"
