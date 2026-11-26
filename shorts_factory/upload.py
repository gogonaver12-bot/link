#!/usr/bin/env python3
"""유튜브 업로드 + 성과 수집 (YouTube Data API v3, 본인 계정 OAuth).

준비(1회): Google Cloud 콘솔 > YouTube Data API v3 사용 > OAuth 클라이언트(데스크톱) 생성
          > client_secret.json 을 이 폴더에 저장.  pip install google-api-python-client google-auth-oauthlib
사용:  python upload.py out/001.mp4 [--private]   업로드 (AI 합성 콘텐츠 표시 자동 ON)
       python upload.py --stats                    올린 영상 조회수/좋아요 -> stats.csv 갱신
"""
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).parent
TOKEN, SECRET, LOG = ROOT / "token.json", ROOT / "client_secret.json", ROOT / "uploads.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]


def yt(story=False):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import os
    # 스토리(AI 실사 드라마)는 별도 채널 토큰 → 정보 숏츠는 F ai-LAB 토큰 → 없으면 기존 계정
    token = ((os.getenv("YOUTUBE_STORY_REFRESH_TOKEN") if story else None)
             or os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN") or os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN"))
    if token:  # 깃허브 Actions: Secrets 의 refresh token 사용 (브라우저 로그인 없음)
        creds = Credentials(None, refresh_token=token, token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.environ["GOOGLE_OAUTH_CLIENT_ID"], client_secret=os.environ["GOOGLE_OAUTH_CLIENT_SECRET"])
        creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)
    creds = Credentials.from_authorized_user_file(TOKEN, SCOPES) if TOKEN.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow  # PC에서 처음 로그인할 때만 필요
            creds = InstalledAppFlow.from_client_secrets_file(SECRET, SCOPES).run_local_server(port=0)
        TOKEN.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(path, private):
    from googleapiclient.http import MediaFileUpload
    meta = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    title = meta["title"][:90] + " #shorts"
    import os
    story = bool(meta.get("story"))
    brand = os.getenv("STORY_CHANNEL_NAME" if story else "CHANNEL_NAME", "")
    tail = (f"\n\n🎬 {brand} — 매일 이어지는 AI 실사 드라마 · 구독하고 다음 화 받아보기" if story
            else f"\n\n🔬 {brand} — AI로 만드는 신기한 실험실 · 구독하고 매일 받아보기")
    desc = meta.get("description", "") + (tail if brand else "")
    body = {"snippet": {"title": title, "description": desc,
                        "tags": meta.get("tags", []), "categoryId": "22", "defaultLanguage": "ko"},
            "status": {"privacyStatus": "private" if private else "public",
                       "selfDeclaredMadeForKids": bool(meta.get("made_for_kids")), "containsSyntheticMedia": True}}
    try:
        r = yt(story).videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(path, resumable=True)).execute()
    except Exception as e:
        if "uploadLimitExceeded" in str(e) or "exceeded the number of videos" in str(e):
            sys.exit("⏸ 유튜브 하루 업로드 한도 초과 — 영상은 만들어 뒀고 내일 자동으로 다시 올려요")
        raise
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    from datetime import date
    log.append({"id": r["id"], "file": Path(path).name, "title": meta["title"], "date": date.today().isoformat(),
                "private": bool(private), "channel": ("story" if story and os.getenv("YOUTUBE_STORY_REFRESH_TOKEN") else
                            "new" if os.getenv("YOUTUBE_OAUTH_REFRESH_TOKEN") else "old"),
                "cover": meta.get("cover", ""), "duration": meta.get("duration")})
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))
    print(f"✅ https://youtube.com/shorts/{r['id']}")


def stats():
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    if not log:
        sys.exit("업로드 기록 없음")
    api, rows = yt(), []
    for i in range(0, len(log), 50):
        chunk = log[i:i + 50]
        res = api.videos().list(part="statistics", id=",".join(v["id"] for v in chunk)).execute()
        st = {it["id"]: it["statistics"] for it in res["items"]}
        for v in chunk:
            s = st.get(v["id"], {})
            # 시청지속률은 Analytics API 필요 -> 스튜디오 값 수동 입력(기본 0)
            rows.append({"file": v["file"], "title": v["title"], "views": s.get("viewCount", 0),
                         "avg_view_pct": 0, "likes": s.get("likeCount", 0), "subs_gained": 0})
    with (ROOT / "stats.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"📊 stats.csv 갱신 ({len(rows)}개)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?")
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    stats() if a.stats else upload(a.video, a.private) if a.video else ap.print_help()
