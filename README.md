# LINK 마더 에이전트 — AI 회사 자동 운영 시스템

목표 한 줄 → CEO(마더)가 팀 배정·신규 채용 → 실행 → 채점 → 프롬프트 자동 업그레이드.
사업은 발굴 → 채점 → 매출 기록 → ROI 리뷰 → **확장 / 개선 / 탈락** → 교훈이 다음 발굴에 반영됩니다.

## 1. 시작 (5분)
1. 저장소 **Settings → Secrets → Actions** 에 `ANTHROPIC_API_KEY` 등록 + 무료 AI 키 1개 이상 추천 (`GEMINI_API_KEY`, `GROQ_API_KEY` 등, 목록은 `.env.example`)
2. **Actions → mother-agent → Run workflow** → 끝. 매일 06:43(KST) 자동 실행, 결과는 `reports/`에 커밋됨
3. 폰에서도: `jarvis/jobs.json`에 `{"id":"job-1","task":"할 일"}` 추가 커밋 → 자동 처리 → `reports/jobs/`

로컬: `pip install -r requirements.txt && export ANTHROPIC_API_KEY=...`

## 📱 휴대폰 앱
**https://gogonaver12-bot.github.io/link/** — 홈 화면에 추가하면 앱처럼 실행 (사업·팀·AI·보고서·명령)
- 🏋️ 회원 운동·식단 관리: **https://gogonaver12-bot.github.io/link/fitness/** (루틴·스케줄·식단·관리표, 회원 공유 링크) · 표 보기: `fitness/routines/` · 생성: `python -m mother fitness`
- 최초 1회: 저장소 Settings → Pages → Branch `main` / `(root)` → Save
- 앱에서 바로 실행하려면: 앱 ⚙️ 설정 → 깃허브 토큰(이 저장소만, Actions 읽기/쓰기) 붙여넣기

## 2. 모든 AI 통합 (16종)
Claude · Gemini · Groq · Cerebras · OpenRouter · Mistral · Ollama(내 PC) · ChatGPT · DeepSeek · Grok · Qwen · Kimi · Together · Upstage Solar · 네이버 HyperCLOVA X · Perplexity
- **키만 Secrets에 넣으면 자동 연결** (`.env.example` 참고). 새 AI는 `config.yaml → providers`에 한 줄 추가
- 실무팀은 **무료 AI 먼저** → 한도 초과·장애면 다음 AI → 마지막 Claude (자동 전환)
- 마더(계획·검수)는 Claude 고정 · 모델 이름은 목록에서 자동 선택(단종 대비)
- 검수 점수가 평균 5.5 미만인 모델은 **자동 탈락**, `ai arena`로 AI끼리 같은 문제 대결 → 성적표
- 에이전트별 고정도 가능: `agents/*.yaml`에 `model: gemini` 또는 `model: openai:모델명`

## 3. 명령어
| 하고 싶은 것 | 명령 | 토큰 |
|---|---|---|
| 회사처럼 목표 처리 | `python -m mother run "일본 BOOTH용 AI 템플릿 판매 시작"` | 사용 |
| 팀에 직접 지시 | `python -m mother ask viral_analyst "미국 쇼츠 바이럴 공식"` | 사용 |
| 사업 발굴 (국가별) | `python -m mother biz scout --market US` | 사용 |
| 매출/비용 기록 | `python -m mother biz log I0001 --revenue 30000 --currency KRW` | 0 |
| ROI 리뷰·탈락 판정 | `python -m mother biz review` | 결정 건만 |
| 에이전트 생성 | `python -m mother agent new tiktok_ops "틱톡 계정 운영"` | 1회 |
| 저성과 에이전트 개선 | `python -m mother agent upgrade` | 해당 건만 |
| 구글/깃허브/스킬/바이럴 검색 | `python -m mother search google\|github\|skills\|prompts\|agents\|youtube\|trending "검색어" --region JP` | **0** |
| 크롤링 | `python -m mother crawl https://...` | **0** |
| 깃허브 스킬 장착 | `python -m mother skill owner/repo path/SKILL.md --agent researcher` | **0** |
| AI 연결 현황·모델 성적표 | `python -m mother ai status` | 0 |
| 가장 싼 AI에 바로 질문 | `python -m mother ai ask "질문"` | 최소 |
| AI 대결(모델 평가) | `python -m mother ai arena "과제"` | 사용 |
| 숏츠 자동 제작 | `cd shorts_factory && ./factory.sh` (대본→음성·자막→MP4→업로드→피드백) | 최소 |
| 현황 | `python -m mother status` | 0 |

## 4. 조직도 (`agents/*.yaml`, 마음대로 수정·추가)
시장조사 · 오픈소스/프롬프트 탐색 · 바이럴 분석 · 콘텐츠 제작(영상 대본) · 판매/마케팅 · 개발 · 현지화(다국어) · 재무분석
→ 부족하면 CEO가 **자동 채용**, 점수 낮으면 **자동 업그레이드**(이전 버전은 `agents/_history/`)

## 5. 토큰 절약 장치
- 하루 예산 상한(`config.yaml` → `budget.daily_usd`), 넘으면 자동 정지 · 비용 장부 `data/usage.jsonl`
- 프롬프트 캐싱(반복 입력 ~90% 할인) · 크롤/검색 결과 디스크 캐시 · 팀 간 전달은 요약만
- 실무팀은 낮은 effort, 키 없는 도구 자동 제외, 검색·크롤은 LLM 없이도 실행
- 무료 AI 키 1개만 넣어도 실무팀 비용 대부분 0원 · Claude 실무팀을 더 아끼려면 `models.worker: claude-haiku-5-5`

## 6. 수익 판정 규칙 (`config.yaml → business`)
- 채점: 수요 25% · 경쟁 15% · 초기비용 15% · 수익속도 20% · 확장성 15% · 리스크 10% → 65점 이상만 실행
- ROI ≥ 100% → **확장** / 30일 경과 & ROI ≤ -30% → **탈락**(교훈 저장) / 그 외 → **개선 계획**
- 시장: 한국·미국·일본·글로벌 (요일별 순환 발굴, `markets`에 국가 추가 가능)

## 7. 원칙
불법·약관위반(가짜 계정 대량생성, 허위리뷰, 스팸, 무단 크롤링)은 제외. 크롤러는 robots.txt를 지키고, 계정·API키는 `.env` / GitHub Secrets로만 관리합니다.

## 8. 이전 프로젝트에서 가져온 것
- `jarvis-ai-hub` → 여러 AI 연결·모델 자동선택·장애 시 자동전환 방식 (`mother/providers.py`)
- `shorts-video-monetization` 브랜치 → 숏츠 공장 (`shorts_factory/`, 피드백을 모든 AI 라우터로 교체)
