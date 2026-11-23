@echo off
chcp 65001 >nul
cd /d %~dp0
echo [1/2] 필요한 프로그램 설치 중...
python -m pip install -q --disable-pip-version-check google-auth-oauthlib google-api-python-client
echo [2/2] 구글 로그인 창을 엽니다...
python google_login.py
pause
