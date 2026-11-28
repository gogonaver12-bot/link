## 5. Ollama(Llama 3) 로컬 폴백(Fallback) 엔진 연동

외부 클라우드 LLM(Anthropic Claude) 장애 시, 사내 인프라를 지키는 최후의 보루는 온프레미스 환경에서 구동되는 로컬 LLM이다. 이번 장에서는 Llama 3 8B 모델을 기반으로 한 Ollama 엔진을 구축하고, 메인 API 장애 시 0.5초 이내에 트래픽을 우회시키는 어댑터 패턴과 페일오버(Failover) 로직을 구현한다.

---

### 1단계: 온프레미스 Ollama 서버 Docker 컨테이너 배포

보안이 철저한 제조·물류 현장의 폐쇄망(Air-gapped) 환경을 기준으로 한다. GPU(NVIDIA A10 또는 RTX 4090 이상 권장)가 장착된 인프라 서버에 접속하여 Docker를 통해 Ollama를 구동한다.

**실행 명령어 (터미널 복붙용):**
```bash
# 1. GPU 지원 Docker 컨테이너 실행 (포트 11434 사용)
docker run -d \
  --gpus=all \
  -v ollama_data:/root/.ollama \
  -p 11434:11434 \
  --name ollama-local \
  --restart always \
  ollama/ollama:latest

# 2. 컨테이너 내부로 진입하여 Llama 3 8B 모델 다운로드 및 구동
docker exec -it ollama-local ollama run llama3:8b
```
> **[현장 체크리스트]**
> * NVIDIA Container Toolkit이 사내 서버에 정상 설치되어 있는지 확인 (`docker run --gpus all nvidia/cuda:11.6.0-base-ubuntu20.04 nvidia-smi`)
> * 폐쇄망 환경인 경우, 외부 인터넷 차단 전 미리 `ollama/ollama:latest` 이미지와 `llama3:8b` 웨이트 파일을 사내 레지스트리에 적재할 것.

---

### 2단계: Anthropic API ⇄ Ollama 포맷 변환 어댑터 패턴 구현

Anthropic API와 Ollama(Llama 3)는 요청/응답 JSON 스키마가 다르다. 게이트웨이 내부에서 표준 어댑터(Adapter) 패턴을 적용하여, 클라이언트의 수정 없이 페이로드를 실시간 변환해야 한다.

**Python 기반 어댑터 핵심 로직 (복붙해서 사용):**
```python
import requests
import json

class LLMAdapter:
    @staticmethod
    def convert_anthropic_to_ollama(anthropic_payload: dict) -> dict:
        """
        Anthropic API 스키마를 Ollama(Llama 3) 포맷으로 변환
        """
        messages = []
        # 시스템 프롬프트가 있는 경우 메시지 리스트에 추가
        if "system" in anthropic_payload:
            messages.append({"role": "system", "content": anthropic_payload["system"]})
        
        # 대화 히스토리 매핑
        for msg in anthropic_payload.get("messages", []):
            messages.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })

        ollama_payload = {
            "model": "llama3:8b",
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": anthropic_payload.get("temperature", 0.7),
                "num_predict": anthropic_payload.get("max_tokens", 1024)
            }
        }
        return ollama_payload

    @staticmethod
    def convert_ollama_to_anthropic(ollama_response: dict) -> dict:
        """
        Ollama 응답을 Anthropic 표준 응답 스키마로 역변환 (클라이언트 호환성 유지)
        """
        content_text = ollama_response.get("message", {}).get("content", "")
        
        return {
            "id": "msg_fallback_local",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": content_text
                }
            ],
            "model": "llama3-8b-local-fallback",
            "stop_reason": "end_turn"
        }
```

---

### 3단계: 0.5초 이내 로컬 모델 자동 전환(Failover) 테스트

메인 API(Anthropic) 호출 시 타임아웃(Timeout) 또는 5xx 서버 에러가 발생할 때, 서킷 브레이커(Circuit Breaker)가 즉시 작동하여 Ollama로 라우팅을 전환하는 테스트를 수행한다.

**FastAPI 기반 게이트웨이 페일오버 라우터 예시:**
```python
from fastapi import FastAPI, HTTPException, Request
import httpx

app = FastAPI()
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_URL = "http://localhost:11434/api/chat"

@app.post("/v1/messages")
async def proxy_gateway(request: Request):
    body = await request.json()
    headers = dict(request.headers)
    
    async with httpx.AsyncClient() as client:
        # 1. 메인 Anthropic API 호출 시도 (타임아웃 0.5초 설정)
        try:
            response = await client.post(
                ANTHROPIC_URL, 
                json=body, 
                headers={
                    "x-api-key": headers.get("x-api-key"),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                timeout=0.5 # 0.5초 초과 시 즉시 장애로 간주
            )
            if response.status_code >= 500:
                raise httpx.RequestError("Anthropic Server Error")
            
            return response.json()

        except (httpx.TimeoutException, httpx.RequestError):
            # 2. 장애 감지 시 Ollama 폴백 엔진 즉시 호출
            ollama_body = LLMAdapter.convert_anthropic_to_ollama(body)
            
            try:
                fallback_response = await client.post(
                    OLLAMA_URL, 
                    json=ollama_body, 
                    timeout=2.0
                )
                raw_ollama = fallback_response.json()
                return LLMAdapter.convert_ollama_to_anthropic(raw_ollama)
                
            except Exception as e:
                raise HTTPException(status_code=503, detail=f"All LLM backends failed: {str(e)}")
```

> **[현장 검증 체크리스트]**
> * Anthropic API 방화벽을 임의 차단(`iptables` 등 활용)하거나 잘못된 API 키를 입력하여 장애 상황 시뮬레이션 수행.
> * 로그(Log) 상에서 메인 API 에러 발생 후 Ollama 응답 반환까지 소요된 시간이 **0.5초(500ms) 이내**인지 확인.
> * 제조 현장의 바코드 스캔 연동 및 물류 라우팅 추천 API 호출 시, 폴백 상태에서도 응답 포맷 불일치로 인한 시스템 에러가 발생하지 않는지 최종 점검.
