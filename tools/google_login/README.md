# 구글 1회 연결 (유튜브·블로그 자동 업로드)

1. [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com) · [Blogger API](https://console.cloud.google.com/apis/library/blogger.googleapis.com) → **사용**
2. [OAuth 동의 화면](https://console.cloud.google.com/auth/overview): 외부 · 앱 이름·이메일 입력 → 대상(Audience)에 내 이메일 테스트 사용자 추가 → **앱 게시(프로덕션)**
3. [OAuth 클라이언트 만들기](https://console.cloud.google.com/auth/clients/create): 유형 **데스크톱 앱** → 만들기 → **JSON 다운로드** → 이 폴더에 `client_secret.json` 으로 저장
4. **google_login.bat 더블클릭** → 브라우저에서 계정 선택 → (경고 시 '고급' → '이동') → **허용**
5. 나온 값 4개를 GitHub Secrets에 붙여넣기 (GitHub CLI 로그인돼 있으면 자동 저장)

`client_secret.json` 은 저장소에 올리지 마세요(.gitignore 처리됨).
