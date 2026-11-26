## 2. GitHub 오픈소스 초안 작성 및 환경 세팅

아이디어가 아무리 좋아도 코드가 꼬여 있거나 API 키가 유출되면 서비스는 오픈하기도 전에 끝난다. 이번 장에서는 비용 폭탄을 원천 차단하고 누구나 가져다 쓸 수 있는 견고한 마이크로SaaS의 뼈대를 만든다. 

군더더기는 다 빼고, 당장 터미널을 열어서 복붙하고 실행할 수 있는 실전 세팅만 진행한다.

---

### 1. 프로젝트 구조 설계 및 기본 디렉토리 생성

무료 LLM(Ollama)과 유료 LLM(Groq)을 매끄럽게 오가는 라우팅 서버의 핵심은 **관심사의 분리**다. 라우팅 로직, API 호출, 예외 처리가 한 파일에 섞이면 나중에 유지보수가 불가능하다.

프로젝트 이름은 `llm-fallback-router`로 통일한다. 터미널에 아래 명령어를 입력해 뼈대를 만든다.

```bash
mkdir llm-fallback-router
cd llm-fallback-router
mkdir -p src/routes src/services src/utils
touch src/index.js src/services/llmService.js src/utils/logger.js .env .env.example .gitignore README.md package.json
```

**디렉토리 구조 역할 요약:**
* `src/index.js`: 서버 진입점 및 라우팅 엔드포인트 정의
* `src/services/llmService.js`: Groq와 Ollama 호출 및 폴백(Fallback) 핵심 로직
* `src/utils/logger.js`: 에러 및 라우팅 성공 여부 기록용 유틸
* `.env`: 실제 API 키 (절대 Git에 올리면 안 됨)
* `.env.example`: 팀원이나 오픈소스 사용자를 위한 환경 변수 템플릿

---

### 2. 필수 라이브러리 설치 및 의존성 관리 설정

가볍고 빠르게 서버를 띄우기 위해 Node.js와 Express를 사용한다. 환경 변수 관리를 위한 `dotenv`, HTTP 요청을 위한 `axios`(또는 공식 SDK)를 설치한다.

먼저 `package.json` 기본 설정을 마친다.

**`package.json` 복붙용 템플릿:**
```json
{
  "name": "llm-fallback-router",
  "version": "1.0.0",
  "description": "Ollama와 Groq를 활용한 무료 LLM 폴백 라우팅 마이크로SaaS",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js"
  },
  "dependencies": {
    "dotenv": "^16.4.5",
    "express": "^4.19.2",
    "groq-sdk": "^0.3.0"
  }
}
```

터미널에서 아래 명령어로 패키지를 설치한다. (Node.js가 설치되어 있어야 한다.)
```bash
npm install
```

---

### 3. 환경 변수(.env) 보안 관리 및 API 키 분기 처리

개발할 때 가장 많이 하는 실수가 Groq API 키를 소스 코드에 하드코딩해서 GitHub에 그대로 올리는 것이다. 이러면 몇 시간 만에 크롤링 당해서 수십만 원의 요금 폭탄을 맞는다. 

`.env` 파일에는 실제 키를 넣고, `.env.example`에는 빈 껍데기를 만들어 소스 제어(Git)에 포함시킨다.

**`.env` (실제 키 입력 - 절대 Git에 올리지 말 것):**
```env
PORT=3000
GROQ_API_KEY=gsk_실제당신의키를넣으세요여기에
OLLAMA_BASE_URL=http://localhost:11434
PRIMARY_LLM=ollama
```

**`.env.example` (Git에 커밋할 템플릿):**
```env
PORT=3000
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_BASE_URL=http://localhost:11434
PRIMARY_LLM=ollama
```

**`.gitignore` 설정:**
프로젝트 루트의 `.gitignore` 파일에 아래 내용을 반드시 추가한다.
```text
node_modules/
.env
.DS_Store
```

---

### 4. GitHub 퍼블릭 리포지토리 오픈 및 README 작성법

오픈소스 마이크로SaaS의 첫인상은 README에서 결정된다. 방문자가 오자마자 "이게 내 서버 비용을 아껴주겠구나" 바로 이해할 수 있어야 한다.

**`README.md` 복붙용 템플릿:**

```markdown
# LLM Fallback Router 🚀

상용 LLM API 비용 폭탄과 서비스 중단(Rate Limit)에 지친 1인 개발자를 위한 오픈소스 폴백 라우팅 마이크로SaaS 백엔드입니다.

1순위로 로컬 무료 LLM(`Ollama`)을 호출하고, 에러나 타임아웃 발생 시 고성능 클라우드 LLM(`Groq`)으로 자동 전환(Fallback)합니다.

## ✨ 주요 기능
- **비용 절감**: 단순 반복 작업은 무료 로컬 LLM으로 처리
- **고가용성**: 로컬 서버 다운 시 Groq API로 자동 우회하여 서비스 중단 방지
- **간단한 통합**: 기존 OpenAI API 스펙과 호환되는 엔드포인트 제공

## 🛠 빠른 시작 (Quick Start)

### 1. 레포지토리 클론 및 설치
```bash
git clone https://github.com/당신의아이디/llm-fallback-router.git
cd llm-fallback-router
npm install
```

### 2. 환경 변수 설정
`.env.example` 파일을 `.env`로 복사하고 키를 입력하세요.
```bash
cp .env.example .env
```

### 3. 서버 실행
```bash
npm run dev
```

## 📜 라이선스
MIT License
```

---

### 💡 장 마감 체크리스트

코딩을 끝내기 전 아래 항목을 눈으로 직접 확인하자. 하나라도 빠졌다면 보안 사고나 실행 에러로 이어진다.

- [ ] `src/` 아래에 필수 디렉토리(`routes`, `services`, `utils`)가 정상 생성되었는가?
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있어 GitHub에 업로드되지 않는가?
- [ ] `npm run dev` 명령어로 에러 없이 서버가 구동되는가?
- [ ] GitHub에 퍼블릭으로 리포지토리가 열렸고 README가 가독성 있게 작성되었는가?

여기까지 완료했다면 비용 폭탄을 막는 1차 방어선 구축이 끝났다. 다음 장에서는 로컬 Ollama와 Groq API를 엮어 실제로 요청을 받아내고 예외를 가로채는 핵심 라우팅 로직을 구현한다.
