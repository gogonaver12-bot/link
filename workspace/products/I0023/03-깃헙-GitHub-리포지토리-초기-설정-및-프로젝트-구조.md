## 3. 깃헙(GitHub) 리포지토리 초기 설정 및 프로젝트 구조

프로덕션 환경에서 운영되는 LLM 장애 복구 게이트웨이는 '멈추지 않는 안정성'이 생명이다. 실험용 코드가 아니라 실제 제조·물류 현장의 미션 크리티컬(Mission-Critical) 시스템을 지탱할 수 있도록, 처음부터 확장성과 보안이 담보된 구조로 리포지토리를 세팅해야 한다.

이 장에서는 Anthropic API와 Ollama(Llama 3) 간의 무중단 폴백(Fallback)을 처리할 FastAPI 기반 프로덕션급 프로젝트의 뼈대를 구축한다.

---

### 3.1 프로덕션급 FastAPI 디렉토리 구조 생성

단일 파일(`main.py`) 중심의 구조는 유지보수를 지옥으로 만든다. 라우터, 비즈니스 로직(폴백 엔진), 설정, 예외 처리를 명확히 분리한 구조를 생성한다.

터미널을 열고 아래 명령어를 순서대로 실행해 디렉토리와 초기 파일을 만든다.

```bash
# 프로젝트 디렉토리 생성 및 이동
mkdir -p llm-fallback-gateway/app/{api/v1,core,services,schemas}
cd llm-fallback-gateway

# 기본 파일 생성
touch app/__init__.py
touch app/main.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/api/v1/endpoints.py
touch app/core/__init__.py
touch app/core/config.py
touch app/core/security.py
touch app/services/__init__.py
touch app/services/fallback_proxy.py
touch app/schemas/__init__.py
touch app/schemas/llm.py
touch .env
touch .env.example
touch pyproject.toml
touch README.md
```

**생성된 디렉토리 역할 요약:**
* `app/main.py`: FastAPI 앱 인스턴스 생성 및 미들웨어 설정
* `app/api/v1/`: API 엔드포인트 라우터 (v1 버전 관리)
* `app/core/`: 설정(`config.py`), 보안 및 인증(`security.py`)
* `app/services/`: Anthropic 호출 및 Ollama 폴백 로직 등 핵심 비즈니스 로직
* `app/schemas/`: Pydantic 데이터 검증 모델

---

### 3.2 `pyproject.toml` 기반 의존성 관리

의존성 관리는 최신 Python 표준인 `pyproject.toml`을 사용한다. 가볍고 빠른 FastAPI 구동을 위해 `uvicorn`, 환경 변수 관리를 위한 `pydantic-settings`, HTTP 요청을 위한 `httpx`를 필수로 지정한다.

복사해서 `pyproject.toml`에 붙여넣는다.

```toml
[build-system]
requires = ["setuptools>=61.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "llm-fallback-gateway"
version = "0.1.0"
description = "Anthropic to Ollama Llama 3 Fallback Gateway for Enterprise DX"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.28.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.1",
]

[tool.setuptools.packages.find]
include = ["app*"]
```

**의존성 설치 명령어:**
```bash
python -m venv venv
source venv/bin/activate  # 윈도우: venv\Scripts\activate
pip install --upgrade pip
pip install .
```

---

### 3.3 `.env` 환경 변수 설정 및 보안 인증 관리 템플릿

제조·물류 대기업의 온프레미스 환경에서는 API Key 및 내부망 Ollama 서버 주소가 외부로 유출되거나 하드코딩되면 치명적이다. `.env` 파일은 절대 깃(Git)에 커밋하지 않도록 `.gitignore`에 등록해야 한다.

#### 1) `.gitignore` 파일 생성
```bash
echo -e "__pycache__/\nvenv/\n.env\n.DS_Store" > .gitignore
```

#### 2) `.env.example` (템플릿 파일 - 깃 커밋 허용)
다른 개발자나 인프라 담당자가 참고할 수 있는 설정 원본 템플릿이다.
```ini
# App Config
APP_ENV=production
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Primary LLM (Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
ANTHROPIC_TIMEOUT=30.0

# Fallback LLM (On-Premise Ollama Llama 3)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=llama3:8b
OLLAMA_TIMEOUT=60.0

# Gateway Security Token (Internal API Auth)
GATEWAY_API_KEY=your-internal-secure-gateway-token
```

#### 3) `app/core/config.py` (Pydantic Settings 연동)
환경 변수를 안전하게 불러오고 타입 검증을 수행하는 설정 파일이다.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "production"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    ANTHROPIC_API_KEY: str
    ANTHROPIC_TIMEOUT: float = 30.0
    
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_NAME: str = "llama3:8b"
    OLLAMA_TIMEOUT: float = 60.0
    
    GATEWAY_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
```

---

### 3.4 3장 구축 완료 체크리스트

프로젝트 초기화가 올바르게 되었는지 아래 항목으로 최종 검증한다.

- [ ] `git status` 실행 시 `.env` 파일이 트래킹되지 않고(Git에 안 올라감), `pyproject.toml`, `app/` 디렉토리만 나타나는가?
- [ ] `python -c "from app.core.config import settings; print(settings.APP_ENV)"` 명령어가 에러 없이 실행되는가?
- [ ] `uvicorn app.main:app --reload` 명령어로 서버가 정상 기동되는가?
