## 4. Anthropic API 클라이언트 및 에러 핸들링 구현

제조·물류 현장의 사내 시스템에서 LLM API를 호출할 때 가장 경계해야 할 것은 ‘무한 대기(Hang)’와 ‘불필요한 과금’이다. 물류 바코드 스캔 데이터나 공정 이상 감지 로그를 실시간으로 처리하는 도중 외부 API가 응답 지연을 일으키면, 전체 파이프라인이 멈춘다. 

이번 장에서는 Python의 고성능 비동기 HTTP 클라이언트인 `HTTPX`를 활용해 Anthropic API 호출 모듈을 구현하고, 제조 현장의 까다로운 요구 수준에 맞춘 정교한 예외 처리 및 장애 감지 트립와이어(Tripwire) 메커니즘을 설계한다.

---

### 4.1 HTTPX 기반 비동기 Anthropic 클라이언트 구현

동기 방식의 `requests` 라이브러리는 대규모 동시 요청이 발생하는 물류 관제 환경에서 병목을 만든다. `httpx.AsyncClient`를 사용해 논블로킹(Non-blocking) 방식으로 Anthropic API를 호출하는 기본 모듈을 작성한다.

```python
# client.py
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("GatewayEngine")

class AnthropicClient:
    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com/v1", timeout: float = 15.0):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.headers = {
            "x-api-key": self.api_key,
            ", anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    async def generate(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/messages"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
                
            except httpx.TimeoutException:
                logger.error("Anthropic API 요청 타임아웃 발생")
                raise
            except httpx.HTTPStatusError as e:
                logger.error(f"Anthropic API HTTP 에러: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Anthropic API 네트워크 에러: {str(e)}")
                raise
```

---

### 4.2 타임아웃, Rate Limit, 서버 에러(5xx) 예외 처리 로직

장애 자동 복구 게이트웨이의 핵심은 **어떤 에러에서 즉시 로컬(Ollama)로 전환할 것인가**를 판단하는 것이다. 모든 에러가 폴백을 유발해서는 안 된다.

#### 예외 처리 분류 기준
1. **즉시 폴백 대상 (Failover Trigger)**:
   - `5xx Server Error`: Anthropic 서버 자체의 장애.
   - `TimeoutException`: 네트워크 지연 또는 Anthropic 서비스 지연 (제조 현장 기준 15초 초과 시 즉시 차단).
   - `Rate Limit (429)`: 일시적 과부하 상태이나, 즉시 응답이 필요한 현장 업무를 위해 로컬 모델로 우회.
2. **예외 처리 대상 (No Failover)**:
   - `400 Bad Request`: 프롬프트 구조 오류. 로컬 모델로 넘겨도 동일한 문제가 발생하므로 클라이언트에 즉시 에러 반환.
   - `401/403 Auth Error`: API Key 설정 오류. 인프라 담당자의 즉각적인 조치가 필요하므로 알람 발송 후 중단.

---

### 4.3 장애 감지 트립와이어(Tripwire) 메커니즘 설계

매번 API를 호출할 때마다 타임아웃을 기다리면 시스템 전체의 처리량이 떨어진다. 외부 API가 죽었음을 빠르게 감지하고 일정 시간 동안 아예 Anthropic 호출을 생략한 채 곧바로 Ollama로 향하게 만드는 **트립와이어(서킷 브레이커 패턴)**를 구현한다.

```python
# tripwire.py
import time
import logging

logger = logging.getLogger("Tripwire")

class Tripwire:
    def __init__(self, failure_threshold: int = 3, recovery_time: float = 60.0):
        self.failure_threshold = failure_threshold  # 연속 실패 허용 횟수
        self.recovery_time = recovery_time          # 차단 유지 시간 (초)
        self.failure_count = 0
        self.trip_time = 0.0
        self.is_tripped = False

    def record_success(self):
        if self.is_tripped:
            logger.info("Anthropic API 정상 상태 복구 감지. 트립와이어 해제.")
        self.failure_count = 0
        self.is_tripped = False

    def record_failure(self):
        self.failure_count += 1
        logger.warning(f"Anthropic API 실패 누적: {self.failure_count}/{self.failure_threshold}")
        
        if self.failure_count >= self.failure_threshold:
            self.is_tripped = True
            self.trip_time = time.time()
            logger.critical(f"트립와이어 작동! 향후 {self.recovery_time}초간 Anthropic 호출을 차단하고 Ollama로 직행합니다.")

    def check_state(self) -> bool:
        """True 반환 시 Anthropic 호출 차단 (Ollama 직행)"""
        if not self.is_tripped:
            return False
        
        # 차단 시간이 지났는지 확인 (Half-Open 상태 진입)
        if time.time() - self.trip_time > self.recovery_time:
            logger.info("트립와이어 대기 시간 경과. Anthropic 재시도 허용 (Half-Open).")
            return False
            
        return True
```

---

### 4.4 구현 검증 체크리스트

게이트웨이 라우터에 위 모듈을 결합하기 전, 아래 항목을 반드시 테스트해야 한다.

- [ ] `httpx.AsyncClient` 사용 시 커넥션 풀(Connection Pool)이 정상적으로 해제되는가? (`async with` 구문 확인)
- [ ] 15초 이상의 지연 발생 시 타임아웃 예외가 정확히 `Tripwire.record_failure()`로 전달되는가?
- [ ] 400번대 클라이언트 에러(Bad Request) 발생 시 트립와이어가 오동작하여 실패 횟수를 누적시키지 않는가?
- [ ] 트립와이어 작동 중 설정된 복구 시간(예: 60초) 동안 Anthropic 호출을 생략하고 Ollama(Llama 3)로 100% 트래픽이 우회되는가?
