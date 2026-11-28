## 7. 프로덕션 환경 배포 및 Docker Compose 최적화

실제 제조·물류 현장의 온프레미스 환경에서 LLM 게이트웨이를 안정적으로 운영하려면 프로세스 동시성 처리와 컨테이너 자원 할당이 핵심이다. 본 장에서는 FastAPI 프록시와 Ollama(Llama 3)를 하나의 패키지로 묶어 원클릭으로 배포하는 프로덕션 레벨의 설정을 다룬다.

---

### 1. Gunicorn + Uvicorn 워커 프로세스 설정 최적화

FastAPI는 기본적으로 Uvicorn(ASGI 서버)을 사용하지만, 프로덕션 환경에서는 멀티 프로세스 관리와 안정성을 위해 **Gunicorn**을 프로세스 매니저로 두고, 워커로 Uvicorn을 구동하는 방식을 사용한다.

사내 인프라 서버의 가용 CPU 코어 수를 $N$이라 할 때, Uvicorn 워커 공식 산식은 `(2 x N) + 1`이다. 하지만 LLM API 프록시는 I/O 바운드 작업이 주를 이루므로 과도한 워커 생성은 오히려 오버헤드를 발생시킨다. 4코어 16GB 기준 아래 설정(워커 4개)을 권장한다.

**`gunicorn_conf.py` (복붙해서 사용)**
```python
import multiprocessing

# 바인드 주소 및 포트
bind = "0.0.0.0:8000"

# 워커 프로세스 수 (CPU 코어 수 기준 조정)
workers = 4 
worker_class = "uvicorn.workers.UvicornWorker"

# 타임아웃 설정 (LLM 응답 지연 고려 120초)
timeout = 120
keepalive = 5

# 로깅
accesslog = "-"
errorlog = "-"
loglevel = "info"
```

---

### 2. Docker Compose 원클릭 배포 구성

프록시 서버와 Ollama 엔진, 그리고 외부 트래픽 제어를 위한 Nginx를 하나의 `docker-compose.yml`로 통합한다. 제조·물류 현장의 사내망 서버(NVIDIA GPU 장착 가정)에 즉시 배포할 수 있는 구성이다.

**`docker-compose.yml` (복붙해서 사용)**
```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    container_name: llm_gateway_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - proxy
    restart: always

  proxy:
    build: .
    container_name: llm_gateway_proxy
    environment:
      - ANTHROPIC_API_KEY=sk-ant-xxx...
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - .:/app
    command: gunicorn -c gunicorn_conf.py main:app
    restart: always

  ollama:
    image: ollama/ollama:latest
    container_name: llm_gateway_ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: always

volumes:
  ollama_data:
```

---

### 3. Nginx 리버스 프록시 및 SSL 인증서 적용 가이드

사내 임직원 및 타 시스템(ERP, MES 등)이 안전하게 HTTPS를 통해 LLM 게이트웨이에 접근하도록 Nginx를 설정한다. 사내 자체 인증서(Self-Signed 또는 사내 CA) 적용 기준이다.

**`nginx/conf.d/default.conf` (복붙해서 사용)**
```nginx
server {
    listen 80;
    server_name ai-gateway.internal.local;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name ai-gateway.internal.local;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    location / {
        proxy_pass http://proxy:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE(Server-Sent Events) 및 스트리밍 응답을 위한 설정
        proxy_buffering off;
        proxy_cache off;
        chunked_transfer_encoding on;
        
        # 긴 LLM 응답 시간 대비 타임아웃 연장
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

### 4. 프로덕션 배포 체크리스트

배포 전 아래 항목을 순서대로 점검하여 제조 현장 시스템의 무중단 운영을 담보한다.

* [ ] **GPU 드라이버 확인**: Ollama 컨테이너가 호스트의 NVIDIA 드라이버 및 `nvidia-container-toolkit`을 정상 인식하는지 확인 (`docker run --rm --gpus all ollama/ollama nvidia-smi` 실행 테스트)
* [ ] **Llama 3 모델 사전 적재**: 최초 기동 시 Ollama 내부에서 `ollama run lllama3` 명령을 통해 모델 가중치가 메모리에 로드되는지 확인
* [ ] **SSL 권한 설정**: Nginx 인증서 파일(`.pem`)의 권한이 올바르게 설정되었는지 확인 (`chmod 600`)
* [ ] **방화벽 및 포트 개방**: 사내망 통신을 위해 80, 443 포트가 열려 있는지, 11434 포트는 외부 노출 없이 내부 네트워크로만 제한되었는지 확인
