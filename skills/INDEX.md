# 회사 스킬·프롬프트·에이전트 목록 (자동 생성)

통합 검색: `python -m mother search all "할 일"` · 앱 → 더보기 → 🔎 통합 검색

## 스킬
- **company_work_prompts** — 업무 비서용 프롬프트 15종 — 이메일, 회의록, 주간보고, 기획서, 엑셀, 요약, 보고 문장, 우선순위, 클레임, PPT, 채용, 협상, 매뉴얼, 브레인스토밍 (`skills/company_work_prompts.md`)
- **local-shorts-factory** — Use when the user wants a horror 3D or AI news short rendered with the PC video factory (Supertonic TTS, Blender) instead of the cloud pipel (`skills/local-shorts-factory.md`)
- **reels_team_prompts** — 숏폼 팀 프롬프트 — 레퍼런스 탐색, 성과 분석(조회수 ≥ 구독자 3배), 대본 각색(구조 유지·내용 교체), 표지 문구 5안, 목소리 선택 (`skills/reels_team_prompts.md`)
- **superpowers-code-review** — Use when completing tasks, implementing major features, or before merging to verify work meets requirements (`skills/superpowers-code-review.md`)
- **superpowers-systematic-debugging** — Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes (`skills/superpowers-systematic-debugging.md`)
- **superpowers-tdd** — Use when implementing any feature or bugfix, before writing implementation code (`skills/superpowers-tdd.md`)
- **superpowers-verification** — Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and  (`skills/superpowers-verification.md`)
- **superpowers-writing-plans** — Use when you have a spec or requirements for a multi-step task, before touching code (`skills/superpowers-writing-plans.md`)
- **superpowers-writing-skills** — Use when creating new skills, editing existing skills, or verifying skills work before deployment (`skills/superpowers-writing-skills.md`)
- **video_prompt_dna** — 영상 장면 프롬프트 규칙 (AI 영상·배경 생성용) (`skills/video_prompt_dna.md`)

## 프롬프트
- **ai-collaboration-starter-agents-rules** — Shared project rules (`prompts/ai-collaboration-starter/agents-rules.md`)
- **ai-collaboration-starter-claude-rules** — Claude Code (`prompts/ai-collaboration-starter/claude-rules.md`)
- **ai-collaboration-starter-gemini-rules** — Gemini CLI (`prompts/ai-collaboration-starter/gemini-rules.md`)
- **ai-collaboration-starter-web-chat-prompts** — Claude · Gemini 웹용 복사 프롬프트 (`prompts/ai-collaboration-starter/web-chat-prompts.md`)
- **company-work-prompts** — 회사 업무용 프롬프트 모음 (ChatGPT·Gemini·Claude 공용) (`prompts/company-work-prompts.md`)
- **jarvis-ai-hub-chatgpt-prompt-research** — ChatGPT용 작업 프롬프트 — 프롬프트 자동 연구·개선 (`prompts/jarvis-ai-hub/chatgpt-prompt-research.md`)
- **jarvis-ai-hub-codex-implementer** — Codex 실행 프롬프트 (복사해서 사용) (`prompts/jarvis-ai-hub/codex-implementer.md`)
- **jarvis-ai-hub-prompt-slots** — JARVIS AI HUB 프롬프트 슬롯 (PC 버전에서 가져옴) (`prompts/jarvis-ai-hub/prompt-slots.md`)
- **jarvis-video-factory-agents-rules** — JARVIS Codex instructions (`prompts/jarvis-video-factory/agents-rules.md`)
- **jarvis-video-factory-gemini-rules** — JARVIS — Gemini CLI project instructions (`prompts/jarvis-video-factory/gemini-rules.md`)
- **jarvis-video-factory-prompt-dna** — JARVIS Production Prompt DNA (`prompts/jarvis-video-factory/prompt-dna.md`)

## 에이전트
- **analyst** — 재무·성과분석팀 — 매출·비용·ROI 수치를 분석해 확장/개선/중단을 판단하고 근거와 다음 실험 1개를 제안. (`agents/analyst.yaml`)
- **content_creator** — 콘텐츠 제작팀 — 콘텐츠 제작 에이전트. 1단계 가이드 분석, 2단계 상세 대본/블로그 초안 작성, 3단계 hook_score 검증(70점 필수), 4단계 workspace/content/에 저장 후 전체 결과 출력. (`agents/content_creator.yaml`)
- **developer** — 개발팀 — 판매/자동화 프로그램 제작 에이전트. 1. 오픈소스 재사용(라이선스 준수). 2. 작업 전 API 키/환경 설정 가이드 필수 선행 안내. 3. 견고한 에러 핸들링, 재시도 및 모델 폴백 로직 필수 구현. 4. workspace/code/<프 (`agents/developer.yaml`)
- **github_scout** — 오픈소스·프롬프트 탐색팀 — 깃허브의 유용한 프롬프트·SKILL·에이전트·자동화를 검색·선별한다. 스타 수, 최근성, 라이선스를 엄격 검증한다. API 호출 실패 시 지수 백오프(재시도)를 필수로 적용해 오류를 방지한 뒤 import_skill을 수행 (`agents/github_scout.yaml`)
- **localizer** — 현지화팀 — 콘텐츠·상품문구를 대상 국가의 언어와 문화(결제수단, 화법, 금기, 단위)에 맞게 현지화. 직역 금지. 결과는 workspace/i18n/ 에 저장. (`agents/localizer.yaml`)
- **office_assistant** — 업무 비서팀 — 사장님의 업무 비서. 이메일·회의록·주간보고·기획서·엑셀 수식·문서 요약·고객 응대·발표 구성·채용·협상·매뉴얼·아이디어를 장착된 업무 프롬프트 형식대로 처리한다. 결론 먼저, 표/불릿, 모르는 건 '확인 필요' 표시, 다음 할 일 1 (`agents/office_assistant.yaml`)
- **researcher** — 시장조사팀 — 시장·트렌드 조사 에이전트. API 오류 시 지연 후 자동 재시도하며, 최신 수요 증거를 웹 검색해 출처 URL과 함께 표/불릿으로 보고한다. 유용한 사이트는 add_site로 추가. (`agents/researcher.yaml`)
- **sales** — 판매·마케팅팀 — 상품 기획과 판매 페이지 담당. 플랫폼별(스마트스토어, Gumroad, Etsy, BOOTH 등) 제목·설명·태그·가격전략을 현지 언어로 작성하고 workspace/sales/ 에 저장. 경쟁 가격 근거 제시. (`agents/sales.yaml`)
- **viral_analyst** — 바이럴 분석팀 — 국가별 바이럴 영상/콘텐츠를 분석. 조회수·좋아요 상위 영상의 공통 패턴(후킹 3초, 길이, 제목 구조, 썸네일 요소)을 뽑아 재현 가능한 공식으로 정리. 레퍼런스 탐색·성과 분석은 장착된 숏폼 팀 프롬프트 01·02 형식(조회수 ≥ (`agents/viral_analyst.yaml`)
