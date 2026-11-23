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


def feeds():
    extra = [(f["name"], f["url"], f.get("category", "custom")) for f in store.cfg().get("feeds", [])]
    return DEFAULT_FEEDS + [f for f in extra if f[1].startswith("https://")]


def collect():
    items = store.load_json("news.json", [])
    seen = {i["id"] for i in items}
    added, failed = 0, []
    for name, url, cat in feeds():
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=15)
            r.raise_for_status()
            entries = parse_feed(r.content[:2_000_000])
        except Exception as e:  # 한 출처 실패는 건너뛰고 계속
            failed.append(f"{name}: {type(e).__name__}")
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
    return added, failed


def search(query="", category="", limit=15):
    q = query.lower()
    rows = [i for i in reversed(store.load_json("news.json", []))
            if (not q or q in (i["title"] + " " + i["summary"]).lower()) and (not category or i["category"] == category)]
    return "\n".join(("⚠️인젝션의심 " if i["flag"] else "") + f"- [{i['source']}] {i['title']} | {i['url']}" for i in rows[:limit]) \
        or "결과 없음 (먼저 python -m mother news 로 수집)"
