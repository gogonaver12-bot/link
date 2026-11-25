@echo off
chcp 65001 >nul
cd /d %~dp0
git -C ..\.. pull -q origin main
python -m pip install -q --disable-pip-version-check cryptography
python audio_pack.py
pause
