@echo off
chcp 65001 >nul
cd /d %~dp0
git -C ..\.. pull -q origin main
echo [AI 실사 드라마 채널 연결] 브라우저에서 드라마 채널을 선택하세요
python -m pip install -q --disable-pip-version-check google-auth-oauthlib google-api-python-client
python google_login.py --story
pause
