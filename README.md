# SecureOps

> Docker 기반 AI 피싱탐지 자동화 AIOps 플랫폼

**팀명**: 확실한 OutPut | **선문대학교 AI소프트웨어학과** | 2026

---

## 시스템 아키텍처

```
[사용자 PC]
  └─ Interceptor (Python 백그라운드) ─── URL 감시
         │
         ▼
[Screening 서버 (8004)] ─── 1차 필터링 (URL 패턴 + WHOIS)
         │
     의심 감지 시
         ▼
[대시보드 팝업] ─── 진행 / 취소 / 샌드박스
         │
    샌드박스 선택 시
         ▼
[Gateway (8000)] ─── Pool에서 Docker 컨테이너 할당
         │
         ├──▶ [Model 1 (8001)] ─── HTML 피싱 정밀 검사 (RandomForest, 18피처)
         ├──▶ [Model 2 (8002)] ─── 네트워크 로그 분석 (XGBoost/LightGBM)
         └──▶ [Docker Sandbox] ─── noVNC + Chromium 격리 브라우저
                  │
                  └─ network_agent.py가 5초마다 트래픽 수집
                     → Gateway → Model 2로 자동 전송

[Model 3 (8003)] ─── AIOps 리소스 모니터링 (관리자 전용)
  └─ Docker Pool 크기 자동 조정 + 리소스 이상 탐지
```

### 분산 아키텍처 (사후 확장 계획)

```
메인 PC (Gateway + 대시보드 + Docker Sandbox Pool)
    ├─ 외부 서버 1: Screening + Model-Phishing
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
| 샌드박스 네트워크 수집기 | 5초마다 트래픽 수집 → Gateway → 2번 모델 자동 전송 |
| React 대시보드 | 로그인, 헬스체크, URL 검사, 샌드박스, 관리자 페이지 |
| WandB MLOps | 연동 확인 완료 |
| Docker Compose | 8개 서비스 통합 실행 |

### 🔧 TODO (미구현)

| 기능 | 우선순위 | 담당 |
|------|----------|------|
| Screening 서버 (1차 필터링) | 1순위 | 이종구 |
| 인터셉터 실제 동작 | 2순위 | 이종구 |
| 2번 모델 실제 구현 (네트워크 분석) | 병렬 | 서용준 |
| 3번 모델 AIOps 실제 구현 | 병렬 | 차인택 |
| 프론트엔드 고도화 | 병렬 | 김태호 |
| DB 기반 사용자 인증 | 후순위 | - |
| GitHub Actions CI/CD | 후순위 | - |

---

## 사전 준비

| 도구 | 버전 | 확인 명령 |
|------|------|-----------|
| Python | 3.11+ | `python --version` |
| Docker Desktop | 최신 | `docker --version` |
| Node.js | 20+ | `node --version` |
| Git | 최신 | `git --version` |

---

## 전체 실행 순서 (로컬 개발 모드)

### STEP 1. 레포 클론

```bash
git clone https://github.com/jonggu2020/Sure_OutPut.git
cd Sure_OutPut
```

### STEP 2. 환경변수 파일 생성

#### 루트 .env (Docker Compose용)

```bash
cp .env.example .env
```

`.env` 파일을 열어서 아래 값을 입력:

```env
# WandB (https://wandb.ai/settings 에서 API Key 복사)
WANDB_API_KEY=실제키입력

# JWT (아무 랜덤 문자열로 변경)
JWT_SECRET=my-super-secret-key-change-this

# DB (기본값 사용 가능)
POSTGRES_USER=secureops
POSTGRES_PASSWORD=secureops
POSTGRES_DB=secureops
```

#### Gateway .env (로컬 개발 시 필수)

`gateway/.env` 파일 생성:

```env
MODEL_PHISHING_URL=http://localhost:8001
MODEL_NETWORK_URL=http://localhost:8002
MODEL_AIOPS_URL=http://localhost:8003
JWT_SECRET=change-me-in-production
```

> ⚠️ 로컬에서 각 서버를 개별 실행할 때만 필요. Docker Compose로 실행 시에는 docker-compose.yml에서 자동 설정됨.

### STEP 3. 샌드박스 Docker 이미지 빌드 (최초 1회)

```bash
cd docker/sandbox
docker build -t secureops-sandbox:latest .
cd ../..
```

### STEP 4. 기존 샌드박스 컨테이너 정리

```bash
# Windows CMD
for /f %i in ('docker ps -aq --filter "label=secureops=sandbox"') do docker rm -f %i

# Mac/Linux
docker rm -f $(docker ps -aq --filter "label=secureops=sandbox") 2>/dev/null
```

### STEP 5. Gateway 서버 실행 (터미널 1)

```bash
cd gateway
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**확인 사항:**
```
✅ Docker 연결 성공
🔧 샌드박스 Pool 초기화 (크기: 5)...
   ✓ 컨테이너 생성: secureops-sandbox-6081 → port 6081
   ✓ 컨테이너 생성: secureops-sandbox-6082 → port 6082
   ✓ 컨테이너 생성: secureops-sandbox-6083 → port 6083
   ✓ 컨테이너 생성: secureops-sandbox-6084 → port 6084
   ✓ 컨테이너 생성: secureops-sandbox-6085 → port 6085
✅ Pool 준비 완료: 5개 대기 중
```

### STEP 6. Model-Phishing 서버 실행 (터미널 2)

```bash
cd model-phishing
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**확인 사항:**
```
✅ 모델 로딩 완료: RandomForestClassifier (피처 18개)
```

> ⚠️ `app/ml/phishing_ml_model.pkl` 파일이 있어야 합니다.

### STEP 7. Model-Network 서버 실행 (터미널 3) — 선택

```bash
cd model-network
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

**확인 사항:** Swagger UI http://localhost:8002/docs 접속 가능.

> 이 서버를 띄우면 샌드박스에서 네트워크 트래픽이 5초마다 자동으로 들어옵니다.
> 안 띄워도 Gateway는 정상 동작합니다 (네트워크 분석만 스킵).

### STEP 8. Model-AIOps 서버 실행 (터미널 4) — 선택

```bash
cd model-aiops
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

> 관리자 전용. 안 띄워도 일반 사용자 기능은 정상 동작합니다.
> 안 띄우면 대시보드 헬스체크에서 AIOps가 red로 표시됩니다.

### STEP 9. Frontend 실행 (터미널 5)

```bash
cd frontend
npm install    # 최초 1회
npm run dev
```

> 포트 3000이 예약된 경우 (Hyper-V/Docker): `npx vite --host 0.0.0.0 --port 5173`

### STEP 10. 접속 및 테스트

| 서비스 | URL |
|--------|-----|
| 대시보드 | http://localhost:3000 (또는 5173) |
| Gateway Swagger | http://localhost:8000/docs |
| Model 1 Swagger | http://localhost:8001/docs |
| Model 2 Swagger | http://localhost:8002/docs |
| Model 3 Swagger | http://localhost:8003/docs |

**테스트 순서:**
1. 대시보드 접속 → 로그인 (`admin / admin123`)
2. 대시보드에서 모델 상태 확인 (녹/주황/적)
3. URL 검사 → `https://www.naver.com` 입력 → 결과 확인
4. 결과 카드에서 "샌드박스 모드" 클릭 → noVNC 원격 브라우저 확인
5. 세션 종료 클릭 → 컨테이너 삭제 확인

**최소 실행 구성 (필수 서버만):**

| 터미널 | 서버 | 포트 | 필수 |
|--------|------|------|------|
| 1 | Gateway | 8000 | ✅ |
| 2 | Model-Phishing | 8001 | ✅ |
| 3 | Frontend | 3000/5173 | ✅ |

**전체 실행 구성:**

| 터미널 | 서버 | 포트 | 필수 |
|--------|------|------|------|
| 1 | Gateway | 8000 | ✅ |
| 2 | Model-Phishing | 8001 | ✅ |
| 3 | Model-Network | 8002 | 선택 |
| 4 | Model-AIOps | 8003 | 선택 |
| 5 | Frontend | 3000/5173 | ✅ |

---

## Docker Compose 통합 실행 (대안)

개별 서버 대신 Docker Compose로 한 번에 올릴 수도 있습니다.

```bash
# 환경변수 파일 생성
cp .env.example .env
# .env 파일에서 WANDB_API_KEY 등 설정

# 전체 빌드 + 실행
docker compose up --build

# 백그라운드 실행
docker compose up --build -d

# 로그 확인
docker compose logs -f gateway
docker compose logs -f model-phishing

# 종료
docker compose down
```

| 서비스 | URL |
|--------|-----|
| Gateway | http://localhost:8000/docs |
| Model 1 | http://localhost:8001/docs |
| Model 2 | http://localhost:8002/docs |
| Model 3 | http://localhost:8003/docs |
| Prometheus | http://localhost:9090 |
| cAdvisor | http://localhost:8085 |

---

## 사용자 흐름

### 일반 사용자

```
1. 크롬에서 정상적으로 인터넷 사용
2. [백그라운드] 인터셉터가 URL을 Screening 서버로 전송
3. [백그라운드] Screening: URL 패턴 + WHOIS로 1차 필터링
4. 의심 감지 → 대시보드 팝업 활성화
5. 사용자 선택:
   ├─ [진행]    → 그대로 접속
   ├─ [취소]    → 접속 차단
   └─ [샌드박스] → Docker 격리 환경에서 열기
6. 샌드박스 모드:
   ├─ noVNC로 Chromium 원격 조종
   ├─ Model 1: HTML 피싱 정밀 검사 (자동)
   ├─ Model 2: 네트워크 트래픽 실시간 분석 (자동, 5초마다)
   └─ 위협 발견 시 실시간 알림
7. 세션 종료 → 컨테이너 즉시 삭제 (데이터 완전 소멸)
```

### 관리자

```
- 대시보드: 모든 모델 상태 확인 (1, 2, 3번 포함)
- 관리자 패널:
  ├─ Docker Pool 상태 (대기/사용 중/전체)
  ├─ Pool 크기 수동 조정 (AIOps 자동 조정 예정)
  ├─ 서버 리소스 모니터링 (CPU/메모리/디스크)
  ├─ 개별 컨테이너 강제 삭제
  └─ 컨테이너별 리소스 할당 조정
```

---

## API 엔드포인트 요약

### 인증

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/auth/login` | POST | 로그인 → JWT 토큰 발급 |

### 피싱 검사

| 엔드포인트 | 메서드 | 인증 | 설명 |
|-----------|--------|------|------|
| `/api/phishing/check` | POST | ✅ | URL 피싱 검사 (1번 모델) |
| `/api/phishing/ws/sandbox/{id}` | WS | - | 샌드박스 실시간 감시 |

### 샌드박스

| 엔드포인트 | 메서드 | 인증 | 설명 |
|-----------|--------|------|------|
| `/api/sandbox/assign` | POST | ✅ | 컨테이너 할당 |
| `/api/sandbox/release/{id}` | POST | ✅ | 세션 종료 + 삭제 |
| `/api/sandbox/network-data` | POST | - | 네트워크 에이전트 데이터 수신 (내부) |
| `/api/sandbox/pool` | GET | 🔒 admin | Pool 상태 조회 |
| `/api/sandbox/pool/config` | PUT | 🔒 admin | Pool 설정 변경 |
| `/api/sandbox/container/{id}` | DELETE | 🔒 admin | 컨테이너 강제 삭제 |
| `/api/sandbox/resources` | GET | 🔒 admin | 서버 리소스 조회 |

### 헬스체크

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/health` | GET | 전체 시스템 상태 (녹/주황/적) |

### 네트워크 분석 (2번 모델)

| 엔드포인트 | 메서드 | 인증 | 설명 |
|-----------|--------|------|------|
| `/api/network/analyze` | POST | ✅ | 네트워크 로그 분석 |

### AIOps (관리자 전용)

| 엔드포인트 | 메서드 | 인증 | 설명 |
|-----------|--------|------|------|
| `/api/aiops/status` | GET | 🔒 admin | Docker 리소스 상태 |
| `/api/aiops/anomalies` | GET | 🔒 admin | 이상 탐지 목록 |
| `/api/aiops/sandbox-policy/{id}` | GET | 🔒 admin | 샌드박스 정책 조회 |

---

## 프로젝트 구조

```
secureops/
├── docker-compose.yml
├── .env.example
├── prometheus.yml
├── README.md                        ← 이 파일
│
├── gateway/                         # 메인 FastAPI 서버 (8000)
│   ├── README.md                    # Gateway 전용 가이드
│   ├── .env                         # 로컬 환경변수 (git 무시)
│   └── app/
│       ├── main.py
│       ├── core/                    # 설정, 인증, DB
│       ├── routers/                 # 요청/응답만
│       ├── services/                # 비즈니스 로직
│       └── schemas/                 # 데이터 모델
│
├── model-phishing/                  # 1번 모델 (8001) — 이종구
│   ├── README.md
│   └── app/ml/phishing_ml_model.pkl # 학습된 모델 (18KB)
│
├── model-network/                   # 2번 모델 (8002) — 서용준
│   └── README.md                    # ⭐ 서용준 작업 가이드
│
├── model-aiops/                     # 3번 모델 (8003) — 차인택
│   └── README.md                    # ⭐ 차인택 작업 가이드
│
├── docker/sandbox/                  # 샌드박스 Docker 이미지
│   ├── README.md
│   └── network_agent.py             # 네트워크 수집 에이전트
│
├── interceptor/                     # 백그라운드 에이전트
│   └── README.md
│
└── frontend/                        # React 대시보드 — 김태호
    └── README.md                    # ⭐ 김태호 작업 가이드
```

---

## 역할 분배

| 이름 | 역할 | 담당 | 작업 디렉토리 | README |
|------|------|------|---------------|--------|
| 이종구 | PM / 백엔드 | Gateway, Model 1, Screening, Docker, 인터셉터 | `gateway/`, `model-phishing/` | `gateway/README.md` |
| 서용준 | AI 모델링 | Model 2 (네트워크 로그 분석) | `model-network/` | `model-network/README.md` |
| 차인택 | AIOps | Model 3 (리소스 이상 탐지 + Ollama RAG) | `model-aiops/` | `model-aiops/README.md` |
| 김태호 | 프론트엔드 | React 대시보드, Firebase | `frontend/` | `frontend/README.md` |

> 각 팀원은 자기 디렉토리의 README를 읽고 작업하면 됩니다.
> 다른 팀원의 코드를 건드릴 필요 없습니다.

---

## 개발 규칙

### 코드 구조 원칙

1. **라우터에 로직 금지** — 라우터는 요청/응답만. 로직은 services/에 위임.
2. **서비스 간 직접 호출 금지** — 필요하면 라우터에서 조합.
3. **데이터는 스키마로만** — schemas/의 Pydantic 모델로만 전달.
4. **모델 서버 독립성** — 각 서버는 Gateway를 import하지 않음. HTTP API로만 통신.

### Git 브랜치 전략

```
main              ← 배포 가능 상태만
├── develop       ← 통합 개발 브랜치
│   ├── feat/screening-server      (이종구)
│   ├── feat/interceptor           (이종구)
│   ├── feat/model2-network        (서용준)
│   ├── feat/model3-aiops          (차인택)
│   └── feat/frontend-upgrade      (김태호)
```

### 프로토타입 계정 (개발용)

| 계정 | 비밀번호 | 역할 |
|------|----------|------|
| `user` | `user123` | 일반 사용자 |
| `admin` | `admin123` | 관리자 |

> ⚠️ 프로토타입 전용. 프로덕션에서는 DB 기반 인증으로 교체 필요.

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | FastAPI, PostgreSQL, Redis |
| AI/ML | scikit-learn (RandomForest), XGBoost, LightGBM, LSTM, Isolation Forest |
| AIOps | Prometheus, cAdvisor, Ollama, ChromaDB |
| Sandbox | Docker SDK (docker-py), noVNC, Chromium, Xvfb, x11vnc |
| Interceptor | mitmproxy, pystray, Tkinter |
| Infra | Docker Compose |
| MLOps | GitHub, WandB |
| Frontend | React, TypeScript, Tailwind CSS, Vite |

---

## 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| `getaddrinfo failed` | 모델 서버 URL이 Docker 호스트명 | `gateway/.env`에서 `localhost`로 변경 |
| 토큰 만료 (401) | JWT 60분 만료 | 로그아웃 후 재로그인 |
| 포트 3000 사용 불가 | Hyper-V 포트 예약 | `npx vite --host 0.0.0.0 --port 5173` |
| Chromium FATAL (Docker) | Ubuntu snap 문제 | Debian 기반 이미지 사용 (현재 적용됨) |
| noVNC 검은 화면 | Chromium 크래시 | `docker logs` 확인 |
| noVNC UI 에러 | vnc.html 버그 | vnc_lite.html 사용 (현재 적용됨) |
| 샌드박스 포트 불일치 | Pool 포트 추적 문제 | 컨테이너 전부 정리 후 Gateway 재시작 |
| 모델 더미 응답 | pkl 파일 누락 | `phishing_ml_model.pkl`을 `ml/` 폴더에 복사 |
| gcloud 인증 오류 | Docker 이미지 pull 실패 | `gcloud auth login` → `gcloud auth configure-docker` |
| 샌드박스 자동 종료 | SandboxPage cleanup | 현재 수동 종료만 동작 (수정 완료) |
