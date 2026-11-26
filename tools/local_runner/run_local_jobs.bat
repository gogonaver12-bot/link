@echo off
chcp 65001 >nul
cd /d %~dp0
python run_local_jobs.py
if not "%1"=="auto" pause
