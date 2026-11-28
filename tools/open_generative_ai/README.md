# Open Generative AI (PC 설치)

인스타 릴스(@lazy_owen)에서 소개한 "유료 영상 AI 대신 쓰는 무료 스튜디오"의 정체: **Open Generative AI** (오픈소스, Anil-matcha/Open-Generative-AI).

- 설치: PC에서 `install_open_generative_ai.bat` 더블클릭 → 공식 GitHub 릴리스 v2.0.0 설치 파일을 받아 실행
- **무료인 부분**: 앱 자체 + 내 PC에서 돌리는 로컬 모델(Settings → Local Models: sd.cpp로 이미지, Wan2GP로 영상 — 영상은 NVIDIA 6GB+ 필요)
- **유료인 부분**: "200~600개 모델"은 MuAPI 클라우드 API를 거침 → 생성마다 크레딧 결제 필요(키 넣기 전 사장님 확인)
- 회사 파이프라인 연결: 지금은 하지 않음(무료 HF·Pollinations·Flow로 충분). PC 로컬 Wan2GP가 잘 돌면 `tools/local_runner`처럼 PC 렌더로 연결 가능
- 주의: 이 앱은 "콘텐츠 필터 없음"을 내세우지만 회사 규칙(실존 인물·저작권·선정성 금지)은 그대로 지킨다
