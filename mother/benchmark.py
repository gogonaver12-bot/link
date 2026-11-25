"""유튜브 벤치마크: 최근 조회수 높은 (AI 제작) 숏츠를 매일 수집 → 대본 작가가 주제·형식을 참고(복제 금지) → 계속 개선."""
import datetime as dt
import re
import time

import requests

from . import store, tools

DEFAULT_QUERIES = [("AI 숏츠", "KR", "ko"), ("AI 애니메이션 쇼츠", "KR", "ko"), ("AI generated shorts", "US", "en"),
                   ("ai animation story shorts", "US", "en"), ("신기한 사실 쇼츠", "KR", "ko")]
API = "https://www.googleapis.com/youtube/v3/"


def _secs(iso):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def refresh(days=14, per_query=15):
    """하루 1번: 검색어별로 최근 인기 숏츠를 모아 '하루 평균 조회수' 순으로 저장 (API 할당량 약 600)."""
    old = store.load_json("shorts_benchmark.json", {})
    if old.get("date") == store.today():
        return old
    key = tools.google_key()
    if not key:
        return old
    queries = [tuple(q) for q in store.cfg().get("shorts", {}).get("benchmark_queries", [])] or DEFAULT_QUERIES
    after = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, rows = {}, []
    for q, region, lang in queries:
        try:
            s = requests.get(API + "search", timeout=20, params={
                "part": "id", "q": q, "type": "video", "videoDuration": "short", "order": "viewCount",
                "publishedAfter": after, "regionCode": region, "relevanceLanguage": lang, "maxResults": per_query, "key": key}).json()
            for it in s.get("items", []):
                ids[it["id"]["videoId"]] = q
        except requests.RequestException:
            continue
    id_list = list(ids)
    for i in range(0, len(id_list), 50):
        try:
            v = requests.get(API + "videos", timeout=20, params={
                "part": "snippet,statistics,contentDetails", "id": ",".join(id_list[i:i + 50]), "key": key}).json()
        except requests.RequestException:
            continue
        for it in v.get("items", []):
            sec = _secs(it["contentDetails"].get("duration"))
            if not sec or sec > 70:
                continue
            pub = dt.datetime.fromisoformat(it["snippet"]["publishedAt"].replace("Z", "+00:00"))
            age = max(1.0, (dt.datetime.now(dt.timezone.utc) - pub).total_seconds() / 86400)
            views = int(it["statistics"].get("viewCount", 0))
            rows.append({"id": it["id"], "query": ids.get(it["id"]), "title": it["snippet"]["title"][:120],
                         "channel_id": it["snippet"].get("channelId"), "comments": int(it["statistics"].get("commentCount", 0)),
                         "channel": it["snippet"]["channelTitle"], "tags": (it["snippet"].get("tags") or [])[:8],
                         "seconds": sec, "views": views, "views_per_day": int(views / age),
                         "likes": int(it["statistics"].get("likeCount", 0)), "url": f"https://youtube.com/shorts/{it['id']}"})
        time.sleep(0.2)
    subs = {}
    chans = list({r.get("channel_id") for r in rows if r.get("channel_id")})
    for i in range(0, len(chans), 50):  # 구독자 수 → 조회수/구독자 배수 (채널 크기 덕이 아닌 '형식의 힘')
        try:
            c = requests.get(API + "channels", timeout=20, params={"part": "statistics", "id": ",".join(chans[i:i + 50]), "key": key}).json()
            subs.update({it["id"]: int(it["statistics"].get("subscriberCount", 0) or 0) for it in c.get("items", [])})
        except requests.RequestException:
            pass
    for r in rows:
        sub = subs.get(r.get("channel_id"), 0)
        r["subs"] = sub
        r["ratio"] = round(r["views"] / sub, 1) if sub else None
    outlier = lambda r: (r["ratio"] or 0) >= 3  # 구독자의 3배 이상 = 따라 할 가치가 있는 영상
    rows.sort(key=lambda r: (not outlier(r), -(r["likes"] + r.get("comments", 0)), -r["views_per_day"]))
    data = {"date": store.today(), "top": rows[:40]}
    store.save_json("shorts_benchmark.json", data)
    return data


def brief(n=15):
    """대본 작가에게 줄 참고 요약: 하루 조회수·길이·제목·태그."""
    top = store.load_json("shorts_benchmark.json", {}).get("top", [])[:n]
    if not top:
        return ""
    lines = [f"- {'⭐구독자의 ' + str(r['ratio']) + '배 · ' if (r.get('ratio') or 0) >= 3 else ''}하루 {r['views_per_day']:,}회 · {r['seconds']}초 · {r['title']} · 태그: {', '.join(r['tags'][:4])}" for r in top]
    secs = sorted(r["seconds"] for r in top)
    return (f"최근 {len(top)}개 인기 AI 숏츠(하루 조회수 순, 중앙 길이 {secs[len(secs) // 2]}초):\n" + "\n".join(lines))
