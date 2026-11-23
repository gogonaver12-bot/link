"""상업 이용 가능한 무료 실사 영상 자동 수집.
- NASA: 퍼블릭 도메인, 키 불필요
- Pixabay: 상업 이용 무료 (PIXABAY_API_KEY 있으면 사용)
(JARVIS-VIDEO-FACTORY jarvis/sources.py 방식 차용)
"""
import hashlib, json, os, urllib.parse, urllib.request
from pathlib import Path

UA = {"User-Agent": "shorts-factory/1.0"}
MAX_BYTES = 60 * 1024 * 1024


def _get(url, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.load(r)


def nasa(query, limit=4):
    q = urllib.parse.urlencode({"q": query, "media_type": "video", "page_size": 30})
    items = _get(f"https://images-api.nasa.gov/search?{q}").get("collection", {}).get("items", [])
    urls = []
    words = [w for w in query.lower().split() if len(w) > 2]
    for it in items:
        d = (it.get("data") or [{}])[0]
        title = str(d.get("title", "")).lower()
        if not all(w in title for w in words):  # 제목에 검색어 전부 포함된 것만
            continue
        try:
            files = _get(it["href"], 20)
        except Exception:
            continue
        mp4 = [f for f in files if isinstance(f, str) and f.lower().endswith(".mp4")]
        tier = lambda u: next((i for i, k in enumerate(["~medium", "~large", "~orig"]) if k in u), 9)
        mp4.sort(key=tier)
        if mp4 and tier(mp4[0]) < 9:
            urls.append(mp4[0].replace("http://", "https://"))
        if len(urls) >= limit:
            break
    return urls


def nasa_images(query, limit=4):
    """NASA 고화질 사진 (글자 거의 없음, 퍼블릭 도메인)."""
    q = urllib.parse.urlencode({"q": query, "media_type": "image", "page_size": 40})
    items = _get(f"https://images-api.nasa.gov/search?{q}").get("collection", {}).get("items", [])
    words = [w for w in query.lower().split() if len(w) > 2]
    urls = []
    for it in items:
        d = (it.get("data") or [{}])[0]
        text = (str(d.get("title", "")) + " " + " ".join(d.get("keywords") or [])).lower()
        if not all(w in text for w in words) or "logo" in text or "poster" in text \
                or d.get("center") in ("HQ", "JSC"):  # 행사/인물 사진 제외
            continue
        link = next((l["href"] for l in it.get("links", []) if l.get("render") == "image"), "")
        if link:
            urls.append(link.replace("~thumb", "~large").replace("http://", "https://"))
        if len(urls) >= limit:
            break
    return urls


def pixabay(query, limit=4):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    q = urllib.parse.urlencode({"key": key, "q": query, "per_page": 10, "safesearch": "true"})
    hits = _get(f"https://pixabay.com/api/videos/?{q}").get("hits", [])
    out = []
    for h in hits[:limit]:
        v = h["videos"].get("large") or h["videos"].get("medium")
        if v and v.get("url"):
            out.append(v["url"])
    return out


def download(url, path):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r, open(path, "wb") as f:
            total = 0
            while chunk := r.read(262144):
                total += len(chunk)
                if total > MAX_BYTES:
                    break
                f.write(chunk)
        return path.stat().st_size > 50_000
    except Exception:
        path.unlink(missing_ok=True)
        return False


def fetch(keywords, cache: Path, want=6):
    """키워드별로 영상 받아 cache 폴더에 저장, 경로 목록 반환."""
    cache.mkdir(parents=True, exist_ok=True)
    got = []
    per = max(1, -(-want // max(1, len(keywords))))
    for kw in keywords:
        try:
            urls = pixabay(kw, per) or nasa_images(kw, per)
        except Exception as e:
            print(f"  ⚠️ '{kw}' 검색 실패: {e}")
            continue
        for u in urls:
            ext = ".jpg" if u.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")) else ".mp4"
            p = cache / (hashlib.md5(u.encode()).hexdigest()[:12] + ext)
            if p.exists() or download(u, p):
                got.append(p)
                print(f"  🎞️ {kw}: {p.name}")
    return got
