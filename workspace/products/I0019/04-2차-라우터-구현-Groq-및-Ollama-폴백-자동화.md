## 4. 2차 라우터 구현 - Groq 및 Ollama 폴백 자동화

메인 LLM API(예: OpenAI, Anthropic)가 다운되거나 비용 한계에 도달했을 때, 서비스가 멈추지 않도록 받쳐주는 안전장치가 바로 2차 폴백(Fallback) 라우터다. 이 장에서는 속도가 압도적인 Groq API와 완전 무료인 로컬 LLM(Ollama)을 연동해, 메인 장애 시 0.1초 만에 우회로를 타는 실전 코드를 구현한다.

---

### 1단계: 초고속 무료 인퍼런스 Groq API 연동

Groq는 특수 하드웨어(LPU)를 사용해 토큰 생성 속도가 초당 수백 자에 달한다. 메인 API 장애 시 1순위로 채택하기에 가장 이상적이다.

1. Groq 콘솔에서 API 키를 발급받는다.
2. 환경 변수(`GROQ_API_KEY`)에 저장한다.
3. 아래 코드를 프로젝트에 추가한다. OpenAI SDK와 호환되므로 `base_url`만 바꾸면 끝난다.

```python
from openai import OpenAI
import os

groq_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)

def call_groq(prompt: str, model: str = "llama3-8b-8192") -> str:
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=5.0 # 응답 지연 5초 초과 시 차단
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Groq API 실패: {str(e)}")
```

---

### 2단계: 로컬 환경 Ollama 구동 및 API 연결

Groq마저 레이트 리밋(Rate Limit)에 걸리거나 네트워크가 끊겼을 때의 최종 방어선은 로컬 PC나 저렴한 VPS에서 돌아가는 Ollama다. 비용 0원으로 무제한 호출이 가능하다.

1. 공식 사이트에서 Ollama를 설치하고 모델을 다운로드한다.
    ```bash
    ollama run llama3
    ```
2. 로컬 서버(기본 포트 `11434`)는 OpenAI 호환 엔드포인트를 제공한다. 파이썬으로 연동하는 방법은 다음과 같다.

```python
ollama_client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama", # 로컬이므로미리미정의된더미 키사용
)

def call_ollama(prompt: str, model: str = "llama3") -> str:
    try:
        response = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            timeout=10.0
        )
        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Ollama 로컬 실행 실패: {str(e)}")
```

---

### 3단계: 0.1초 내 폴백 전환 알고리즘 (핵심 로직)

메인 API 호출 시 에러(타임아웃, 429 Rate Limit, 5xx 서버 에러)가 발생하는 즉시 Groq로 넘어가고, Groq저 실패하면 Ollama로 떨어지는 계층형 폴백 함수를 작성한다.

```python
import time

def smart_router(prompt: str, main_call_func) -> tuple[str, str]:
    """
    1순위 메인 API -> 2순위 Groq -> 3순위 Ollama 순으로 폴백 수행
    반환값: (응답 텍스트, 사용된 소스 이름)
    """
    start_time = time.time()
    
    # 1단계: 메인 API 시도
    try:
        res = main_call_func(prompt)
        return res, "Main-API"
    except Exception as main_err:
        print([경고] 메인 API 실패, Groq로 폴백... 에러: {main_err})
        
    # 2단계: Groq 폴백 시도
    try:
        res = call_groq(prompt)
        elapsed = time.time() - start_time
        print(f"[성공] Groq 폴백 완료 (소요 시간: {elapsed:.3f}초)")
        return res, "Groq-Fallback"
    except Exception as groq_err:
        print(f"[경고] Groq API마저 실패, 로컬 Ollama로 긴급 전환... 에러: {groq_err}")
        
    # 3단계: Ollama 최종 폴백 (로컬이므로 네트워크 장애에도 동작)
    try:
        res = call_ollama(prompt)
        elapsed = time.time() - start_time
        print(f"[성공] Ollama 최종 폴백 완료 (소요 시간: {elapsed:.3f}초)")
        return res, "Ollama-Local"
    except Exception as ollama_err:
        raise ConnectionError(f"[치명적] 모든 LLM 인스턴스 응답 불가. Ollama 에러: {ollama_err}")
```

---

### 4단계: 모델 간 응답 포맷(Schema) 일치화 및 파싱 처리

SaaS 서비스에서는 LLM이 JSON 형태의 구조화된 데이터를 반환해야 하는 경우가 많다. 하지만 모델(Llama 3, Mistral 등)마다 JSON 출력을 마크다운 블록(```json ... ```)으로 감싸거나, 쓸데없는 잡담을 앞에 붙이는 버릇이 있다. 이를 강제로 정제하는 파서 함수를 라우터에 붙여야 앱이 죽지 않는다.

```python
import json
import re

def clean_and_parse_json(raw_response: str) -> dict:
    """
    LLM의 날것 응답에서 JSON을 추출하고 스키마를 강제 정제한다.
    """
    # 1. 마크다운 코드 블록 제거
    cleaned = re.sub(r'```json\s*', '', raw_response)
    cleaned = re.sub(r'```\s*', '', cleaned)
    
    # 2. 첫 '{' 와 마지막 '}' 사이의 텍스트만 추출
    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if not match:
        raise ValueError(f"유효한 JSON 포맷을 찾을 수 없음: {raw_response}")
    
    json_str = match.group(0)
    
    try:
        parsed_data = json.loads(json_str)
        return parsed_data
    except json.JSONDecodeError as e:
        # 3차 가공: 따옴표 누락 등 간단한 파싱 에러 방어 로직 추가 가능
        raise ValueError(f"JSON 파싱 실패: {e} / 원본: {json_str}")
```

---

### 💡 실전 체크리스트: 배포 전 반드시 확인 3가지

1. **타임아웃 설정 확인**: 메인 API가 응답 없이 멈춰버리면 사용자는 무한 대기한다. 메인 API 호출 시 `timeout=3.0` (3초)을 반드시 걸어두어 불필요한 대기를 차단했는가?
2. **모델 성능 차이 인지**: 메인이 쓰던 거대한 모델(예: Claude 3.5 Sonnet)에 비해 Groq나 Ollama의 8B급 모델은 논리적 추론 능력이 떨어진다. JSON 스키마 유도 프롬프트(System Prompt)를 더 엄격하게 작성했는가?
3. **로컬 Ollama 데몬 유지**: 서버 배포 시(AWS EC2 등), Ollama가 백그라운드 서비스(`systemd` 등)로 상시 구동되도록 설정했는가?
