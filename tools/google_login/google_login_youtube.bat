@echo off
chcp 65001 >nul
cd /d %~dp0
echo [새 유튜브 채널 연결] 브라우저에서 F ai-LAB 채널을 선택하세요
python -m pip install -q --disable-pip-version-check google-auth-oauthlib google-api-python-client
python google_login.py --youtube
pause
