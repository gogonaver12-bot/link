"""구글 1회 연결 도우미 (PC에서 실행): 브라우저에서 '허용' 한 번 → 자동 업로드용 키 4개를 한 번에 만들어 준다.

준비: 같은 폴더에 client_secret.json (구글 클라우드 → OAuth 클라이언트 '데스크톱 앱' → JSON 다운로드)
실행: google_login.bat 더블클릭  (또는  python google_login.py)
GitHub CLI(gh)가 로그인돼 있으면 Secrets 에 자동 저장, 아니면 값만 보여줌 → 복사해서 붙여넣기.
"""
import json
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

REPO = "gogonaver12-bot/link"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/blogger"]
HERE = Path(__file__).resolve().parent


def main():
    secret_file = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "client_secret.json"
    if not secret_file.exists():
        cands = sorted(HERE.glob("client_secret*.json"))
        if not cands:
            sys.exit("client_secret.json 이 없어요. 구글 클라우드 → OAuth 클라이언트(데스크톱 앱) → JSON 다운로드 → 이 폴더에 저장")
        secret_file = cands[0]
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    print("브라우저가 열리면 내 구글 계정 선택 → (확인되지 않은 앱 경고가 나오면 '고급' → '이동') → 허용")
    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    if not creds.refresh_token:
        sys.exit("refresh token 을 못 받았어요. 다시 실행해서 '허용'을 눌러 주세요.")
    info = json.loads(secret_file.read_text(encoding="utf-8"))
    client = info.get("installed") or info.get("web") or {}

    ch = build("youtube", "v3", credentials=creds, cache_discovery=False).channels().list(part="snippet", mine=True).execute()
    channel = ch["items"][0]["snippet"]["title"] if ch.get("items") else "(유튜브 채널 없음 — youtube.com 에서 채널 만들기)"
    blogs = build("blogger", "v3", credentials=creds, cache_discovery=False).blogs().listByUser(userId="self").execute().get("items", [])
    blog_id = blogs[0]["id"] if blogs else ""

    values = {"GOOGLE_OAUTH_CLIENT_ID": client.get("client_id", ""), "GOOGLE_OAUTH_CLIENT_SECRET": client.get("client_secret", ""),
              "GOOGLE_OAUTH_REFRESH_TOKEN": creds.refresh_token, "BLOGGER_BLOG_ID": blog_id}
    print(f"\n✅ 연결 성공 — 유튜브 채널: {channel} / 블로그: {blogs[0]['name'] if blogs else '없음(blogger.com 에서 하나 만들고 다시 실행)'}")

    gh = shutil.which("gh")
    saved = []
    if gh and subprocess.run([gh, "auth", "status"], capture_output=True).returncode == 0:
        for k, v in values.items():
            if v and subprocess.run([gh, "secret", "set", k, "--repo", REPO], input=v, text=True, capture_output=True).returncode == 0:
                saved.append(k)
    if len(saved) == sum(1 for v in values.values() if v):
        print("🔐 GitHub Secrets 에 자동 저장 완료:", ", ".join(saved))
        return
    print("\n아래 값을 GitHub Secrets 에 하나씩 붙여넣으세요 (Name = 왼쪽, Secret = 오른쪽). 이 창은 닫으면 사라져요.\n")
    for k, v in values.items():
        if k not in saved:
            print(f"{k}\n{v or '(비어 있음)'}\n")
    webbrowser.open(f"https://github.com/{REPO}/settings/secrets/actions/new")
    input("다 넣었으면 Enter 를 눌러 종료")


if __name__ == "__main__":
    main()
