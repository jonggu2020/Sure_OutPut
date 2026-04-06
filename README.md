# SecureOps

> Docker 기반 AI 피싱탐지 자동화 AIOps 플랫폼

**팀명**: 확실한 OutPut | **선문대학교 AI소프트웨어학과** | 2026

**GitHub**: https://github.com/jonggu2020/Sure_OutPut.git

---

## 시스템 아키텍처

```
[사용자 PC]
  └─ SecureOps.exe (브라우저 URL 감시)
         │
         ▼ URL 변경 감지 시
[Gateway (8000)] ─── AI 피싱 검사 요청
         │
         ├──▶ [Model 1 (8001)] ─── HTML 피싱 정밀 검사 (RandomForest, 18피처)
         │
         ├── 검사 결과 → 사용자 PC에 알림 팝업
         │    ├─ 무시      → 그대로 접속
         │    ├─ 강제 접속  → 사용자 책임
         │    └─ 샌드박스   → Docker 격리 환경에서 열기
         │
         ├──▶ [Docker Sandbox] ─── noVNC + Chromium 격리 브라우저
         │         └─ network_agent.py (할당 시에만 활성화)
         │              → Gateway → Model 2로 자동 전송
         │
         └──▶ [Model 2 (8002)] ─── 네트워크 로그 분석 (XGBoost/LightGBM)

[Model 3 (8003)] ─── AIOps 리소스 모니터링 (관리자 전용)
  └─ Docker Pool 크기 자동 조정 + 리소스 이상 탐지
```

### 분산 아키텍처 (사후 확장 계획)

```
메인 PC (Gateway + 대시보드 + Docker Sandbox Pool)
    ├─ 외부 서버 1: Model-Phishing
    ├─ 외부 서버 2: Model-Network
    └─ 외부 서버 3: Model-AIOps + Ollama RAG
```

.env의 URL만 변경하면 코드 수정 없이 분산 가능.

---

## 현재 완성된 기능

### ✅ 완료

| 기능 | 설명 |
|------|------|
| Gateway 서버 | 라우터/서비스/스키마 3계층 분리 |
| JWT 인증 | user/admin 역할 구분 |
| 헬스체크 API | 모델 상태 녹/주황/적 |
| 1번 모델 (HTML 피싱) | RandomForest, 18개 피처, 99.9% 정확도 |
| URL 피처 추출 | URL 패턴 8개 + HTML 크롤링 10개 |
| Docker Sandbox Pool | Warm Pool (기본 5개), 자동 보충, 포트 추적 |
| noVNC 원격 브라우저 | Chromium 격리 환경, URL 자동 전달 |
| 세션 종료 | 컨테이너 즉시 삭제 (보안) |
| 샌드박스 네트워크 수집기 | 할당 시 활성화, 5초마다 수집 → 2번 모델 자동 전송 |
| React 대시보드 | 로그인, 헬스체크, URL 검사, 샌드박스, 관리자 페이지 |
| 인터셉터 (.exe) | 브라우저 URL 감시, GUI 로그인, 알림 팝업, 샌드박스 직접 할당 |
| 외부 접속 | 포트포워딩 + CORS 설정 완료 |
| WandB MLOps | 연동 확인 완료 |

### 🔧 TODO (미구현)

| 기능 | 우선순위 | 담당 |
|------|----------|------|
| Screening 서버 (1차 필터링) | 1순위 | 이종구 |
| 2번 모델 실제 구현 (네트워크 분석) | 병렬 | 서용준 |
| 3번 모델 AIOps 실제 구현 | 병렬 | 차인택 |
| 프론트엔드 고도화 | 병렬 | 김태호 |
| DB 기반 사용자 인증 | 후순위 | - |

---

## 사전 준비

### 서버 (메인 PC)

| 도구 | 버전 | 확인 명령 |
|------|------|-----------|
| Python | 3.11+ | `python --version` |
| Docker Desktop | 최신 | `docker --version` |
| Node.js | 20+ | `node --version` |
| Git | 최신 | `git --version` |

### 클라이언트 (사용자 PC)

SecureOps.exe 파일만 있으면 됩니다. 별도 설치 불필요.

---

## 전체 실행 순서 (서버)

### STEP 1. 레포 클론

```bash
git clone https://github.com/jonggu2020/Sure_OutPut.git
cd Sure_OutPut
```

### STEP 2. Gateway .env 파일 생성

`gateway/.env` 파일 생성:

```env
MODEL_PHISHING_URL=http://localhost:8001
MODEL_NETWORK_URL=http://localhost:8002
MODEL_AIOPS_URL=http://localhost:8003
JWT_SECRET=change-me-in-production
```

### STEP 3. 샌드박스 Docker 이미지 빌드 (최초 1회)

```bash
cd docker/sandbox
docker build -t secureops-sandbox:latest .
cd ../..
```

### STEP 4. 기존 샌드박스 컨테이너 정리

```powershell
# Windows PowerShell
docker ps -aq --filter "label=secureops=sandbox" | ForEach-Object { docker rm -f $_ }
```

### STEP 5. Gateway 실행 (터미널 1)

```bash
cd gateway
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

확인: `✅ Pool 준비 완료: 5개 대기 중`

> ⚠️ `--host 0.0.0.0` 필수! 없으면 외부 접속 불가.

### STEP 6. Model-Phishing 실행 (터미널 2)

```bash
cd model-phishing
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

확인: `✅ 모델 로딩 완료: RandomForestClassifier (피처 18개)`

### STEP 7. Model-Network 실행 (터미널 3) — 선택

```bash
cd model-network
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

### STEP 8. Model-AIOps 실행 (터미널 4) — 선택

```bash
cd model-aiops
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

### STEP 9. Frontend 실행 (터미널 5)

```bash
cd frontend
npm install
npx vite --host 0.0.0.0 --port 5173
```

> ⚠️ `--host 0.0.0.0` 필수!

### STEP 10. 접속 테스트

| 접속 위치 | 대시보드 | Gateway API |
|----------|---------|-------------|
| 로컬 | http://localhost:5173 | http://localhost:8000/docs |
| 외부 | http://123.212.210.230:5173 | http://123.212.210.230:8000 |

로그인: `admin / admin123` 또는 `user / user123`

---

## 인터셉터 (클라이언트)

### 개발 모드

```bash
cd interceptor
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### .exe 빌드

```bash
python build_exe.py
# → dist/SecureOps.exe
```

### 사용자 경험

```
1. SecureOps.exe 더블클릭
2. 첫 실행 → 개인정보 동의 (GUI)
3. 로그인 (GUI)
4. 시스템 트레이에서 백그라운드 실행
5. 브라우저 URL 변경 시 → 자동 검사 → 오른쪽 하단 알림 팝업
6. 팝업: 무시 / 강제 접속 / 샌드박스
7. 트레이 우클릭: 대시보드 / 로그아웃 / 종료
```

---

## 외부 접속 설정

### 공유기 포트포워딩

| 외부 포트 | 내부 IP | 내부 포트 | 설명 |
|----------|---------|----------|------|
| 5173 | 192.168.35.49 | 5173 | Frontend |
| 8000 | 192.168.35.49 | 8000 | Gateway |
| 6081-6090 | 192.168.35.49 | 6081 | 샌드박스 noVNC |

### Windows 방화벽

인바운드 규칙 추가: TCP 포트 `5173, 8000, 6081-6090`

### CORS 설정

`gateway/app/core/config.py`:

```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://123.212.210.230:5173",
]
```

### 주의

- 내부에서 외부 IP로 접속하면 공유기가 뻗을 수 있음 (NAT Loopback 미지원)
- 외부 테스트는 모바일 데이터(WiFi 끄고)로만

---

## 실행 구성 요약

| 터미널 | 서버 | 포트 | 필수 |
|--------|------|------|------|
| 1 | Gateway | 8000 | ✅ |
| 2 | Model-Phishing | 8001 | ✅ |
| 3 | Model-Network | 8002 | 선택 |
| 4 | Model-AIOps | 8003 | 선택 |
| 5 | Frontend | 5173 | ✅ |

---

## 역할 분배

| 이름 | 역할 | 담당 | 작업 디렉토리 |
|------|------|------|---------------|
| 이종구 | PM / 백엔드 | Gateway, Model 1, Docker, 인터셉터 | `gateway/`, `model-phishing/`, `interceptor/` |
| 서용준 | AI 모델링 | Model 2 (네트워크 분석) | `model-network/` |
| 차인택 | AIOps | Model 3 (이상 탐지 + Ollama RAG) | `model-aiops/` |
| 김태호 | 프론트엔드 | React 대시보드 | `frontend/` |

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | FastAPI, Python 3.11 |
| AI/ML | scikit-learn (RandomForest), XGBoost, LightGBM, LSTM, Isolation Forest |
| AIOps | Prometheus, cAdvisor, Ollama, ChromaDB |
| Sandbox | Docker SDK, noVNC, Chromium, Xvfb, x11vnc |
| Interceptor | Tkinter GUI, pystray, UI Automation, PyInstaller |
| Infra | Docker Compose |
| MLOps | GitHub, WandB |
| Frontend | React, TypeScript, Tailwind CSS, Vite |

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| `getaddrinfo failed` | Docker 호스트명 | `gateway/.env`에서 `localhost`로 변경 |
| 토큰 만료 (401) | JWT 60분 만료 | 재로그인, `~/.secureops/config.json` 삭제 |
| 포트 3000 사용 불가 | Hyper-V 예약 | `npx vite --host 0.0.0.0 --port 5173` |
| Chromium FATAL | Ubuntu snap | Debian 기반 이미지 (python:3.12-slim) |
| noVNC UI 에러 | vnc.html 버그 | vnc_lite.html 사용 |
| 샌드박스 about:blank | URL 전달 타이밍 | sleep(3) 대기 |
| Gateway 과부하 | idle 컨테이너 네트워크 전송 | network_agent autostart=false |
| 외부 접속 불가 | --host 0.0.0.0 누락 | Gateway, Frontend 모두 추가 |
| 내부에서 외부 IP 접속 | NAT Loopback 미지원 | 외부 테스트는 모바일 데이터 |
| .exe 서버 연결 실패 | Gateway 미실행 또는 0.0.0.0 미설정 | 확인 후 재시작 |
