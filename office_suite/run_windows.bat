@echo off
chcp 65001 >nul
rem 파이썬이 설치된 PC에서 소스로 바로 실행 (exe 대신)
cd /d "%~dp0.."
python -m pip install -q -r office_suite\requirements.txt
python -m office_suite
if errorlevel 1 pause
