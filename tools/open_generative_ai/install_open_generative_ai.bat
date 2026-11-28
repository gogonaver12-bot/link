@echo off
chcp 65001 >nul
rem Open Generative AI (오픈소스 영상·이미지 스튜디오, MIT) 공식 설치 파일을 받아 설치합니다.
rem 출처: https://github.com/Anil-matcha/Open-Generative-AI/releases (v2.0.0)
set URL=https://github.com/Anil-matcha/Open-Generative-AI/releases/download/v2.0.0/Open.Generative.AI.Setup.2.0.0.exe
set OUT=%TEMP%\OpenGenerativeAI-Setup-2.0.0.exe
echo [1/2] 설치 파일 받는 중 (약 130MB)...
curl -L --fail -o "%OUT%" "%URL%"
if errorlevel 1 (
  echo 다운로드 실패 - 인터넷 연결을 확인하고 다시 실행하세요.
  pause
  exit /b 1
)
echo [2/2] 설치 시작 - 파란 경고창이 뜨면 "추가 정보" - "실행"을 누르세요 (서명 안 된 오픈소스 설치 파일).
start "" "%OUT%"
echo.
echo 설치 후: 시작 메뉴 - Open Generative AI 실행
echo  - 무료로 쓰려면: Settings - Local Models - sd.cpp 엔진 설치 - 모델 다운로드 (이미지, 내 PC에서 생성)
echo  - 영상 무료 생성은 Wan2GP 별도 설치 + NVIDIA 그래픽카드(6GB 이상) 필요
echo  - 600개 클라우드 모델은 MuAPI 유료 크레딧이 필요합니다 (키 넣기 전에 가격 확인)
pause
