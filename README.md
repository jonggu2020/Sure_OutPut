# SecureOps

> Docker 기반 AI 피싱탐지 자동화 AIOps 플랫폼

**팀명**: 확실한 OutPut | **선문대학교 AI소프트웨어학과** | 2025

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
                  └─ 네트워크 트래픽 자동 수집 → Model 2로 전송

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

## 프로젝트 구조

```
secureops/
├── docker-compose.yml              # 전체 인프라 오케스트레이션
├── .env.example                    # 환경변수 템플릿
├── prometheus.yml                  # Prometheus 수집 설정
│
├── gateway/                        # 메인 FastAPI 서버 (포트 8000)
│   ├── app/
│   │   ├── main.py                 # 앱 진입점 + Pool 초기화
│   │   ├── core/
│   │   │   ├── config.py           # 환경변수 관리
│   │   │   ├── security.py         # JWT 인증 + 역할 기반 접근 제어
│   │   │   └── database.py         # PostgreSQL 연결
│   │   ├── routers/
│   │   │   ├── auth.py             # 로그인/토큰 발급
│   │   │   ├── health.py           # 헬스체크 (신호등 API)
│   │   │   ├── phishing.py         # 피싱 검사 + WebSocket
│   │   │   ├── network.py          # 네트워크 분석
│   │   │   ├── aiops.py            # AIOps (관리자 전용)
│   │   │   └── sandbox.py          # 샌드박스 할당/반환/Pool 관리
│   │   ├── services/
│   │   │   ├── phishing_service.py # 1번 모델 통신
│   │   │   ├── network_service.py  # 2번 모델 통신
│   │   │   ├── aiops_service.py    # 3번 모델 통신
│   │   │   ├── sandbox_service.py  # 샌드박스 비즈니스 로직
│   │   │   └── sandbox_pool.py     # Docker Pool 관리 (핵심)
│   │   └── schemas/
│   │       ├── phishing.py         # 피싱 검사 요청/응답
│   │       ├── network.py          # 네트워크 분석 요청/응답
│   │       ├── user.py             # 인증 요청/응답
│   │       └── sandbox.py          # 샌드박스/Pool 요청/응답
│   ├── .env                        # 로컬 환경변수 (git 무시)
│   ├── Dockerfile
│   └── requirements.txt
│
├── model-phishing/                 # 1번 모델 서버 (포트 8001)
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/predict.py      # /predict, /health 엔드포인트
│   │   ├── services/predict.py     # 모델 로딩 + 추론 파이프라인
│   │   └── ml/
│   │       ├── preprocessor.py     # 18개 피처 추출 (URL + HTML 크롤링)
│   │       └── phishing_ml_model.pkl  # 학습된 RandomForest 모델
│   ├── Dockerfile
│   └── requirements.txt
│
├── model-network/                  # 2번 모델 서버 (포트 8002) — 서용준 담당
│   ├── app/main.py                 # 템플릿 (TODO 구현)
│   ├── Dockerfile
│   └── requirements.txt
│
├── model-aiops/                    # 3번 모델 서버 (포트 8003) — 차인택 담당
│   ├── app/main.py                 # 템플릿 (TODO 구현)
│   ├── Dockerfile
│   └── requirements.txt
│
├── docker/
│   └── sandbox/                    # 샌드박스 Docker 이미지
│       ├── Dockerfile              # Debian + Xvfb + x11vnc + noVNC + Chromium
│       ├── supervisord.conf        # 프로세스 관리
│       └── start.sh
│
├── interceptor/                    # Python 로컬 프록시 에이전트
│   ├── main.py                     # 진입점 (프록시 + 트레이)
│   ├── interceptor/
│   │   ├── proxy.py                # mitmproxy 기반 URL 가로채기
│   │   ├── client.py               # Gateway API 통신
│   │   ├── alert.py                # 위험 감지 팝업 (진행/취소/샌드박스)
│   │   └── tray.py                 # 시스템 트레이 아이콘
│   └── requirements.txt
│
└── frontend/                       # React 대시보드
    ├── src/
    │   ├── App.tsx                  # 라우터 설정
    │   ├── components/Layout.tsx    # 사이드바 (admin 메뉴 조건부 표시)
    │   ├── contexts/AuthContext.tsx # 로그인 상태 관리
    │   ├── services/api.ts         # Gateway API 클라이언트
    │   └── pages/
    │       ├── LoginPage.tsx        # 로그인 (JWT)
    │       ├── DashboardPage.tsx    # 헬스체크 신호등
    │       ├── ScanPage.tsx         # URL 검사 + 샌드박스 진입
    │       ├── SandboxPage.tsx      # noVNC 원격 브라우저
    │       └── AdminPage.tsx        # 관리자 전용 (Pool + 리소스)
    ├── vite.config.ts              # Vite + API 프록시 설정
    ├── tailwind.config.js
    └── package.json
```

---

## 현재 완성된 기능 (프로토타입)

### ✅ 완료

| 기능 | 상태 | 설명 |
|------|------|------|
| Gateway 서버 | ✅ | 라우터/서비스/스키마 3계층 분리 |
| JWT 인증 | ✅ | user/admin 역할 구분 |
| 헬스체크 API | ✅ | 모델 상태 녹/주황/적 |
| 1번 모델 (HTML 피싱) | ✅ | RandomForest, 18개 피처, 99.9% 정확도 |
| URL 피처 추출 | ✅ | URL 패턴 8개 + HTML 크롤링 10개 |
| Docker Sandbox Pool | ✅ | Warm Pool (기본 5개), 자동 보충, 포트 추적 |
| noVNC 원격 브라우저 | ✅ | Chromium 격리 환경, URL 자동 전달 |
| 세션 종료 | ✅ | 컨테이너 즉시 삭제 (보안) |
| React 대시보드 | ✅ | 로그인, 헬스체크, URL 검사, 샌드박스 |
| 관리자 페이지 (UI) | ✅ | Pool 관리 + 리소스 모니터링 UI 준비 |
| WandB MLOps | ✅ | 연동 확인 완료 |
| Docker Compose | ✅ | 8개 서비스 통합 실행 |

### 🔧 TODO (미구현)

| 기능 | 우선순위 | 담당 |
|------|----------|------|
| Screening 서버 (1차 필터링) | 1순위 | 이종구 |
| 샌드박스 네트워크 수집기 | 2순위 | 이종구 |
| 인터셉터 실제 동작 | 3순위 | 이종구 |
| 2번 모델 연동 (네트워크 분석) | 병렬 | 서용준 |
| 3번 모델 AIOps 연동 | 병렬 | 차인택 |
| 프론트엔드 고도화 | 병렬 | 김태호 |
| DB 기반 사용자 인증 | 후순위 | - |
| GitHub Actions CI/CD | 후순위 | - |

---

## 실행 방법

### 사전 준비

| 도구 | 버전 | 확인 명령 |
|------|------|-----------|
| Python | 3.11+ | `python --version` |
| Docker Desktop | 최신 | `docker --version` |
| Node.js | 20+ | `node --version` |
| Git | 최신 | `git --version` |

### 방법 1: 로컬 개발 모드 (서버 개별 실행)

#### STEP 1. 샌드박스 Docker 이미지 빌드 (최초 1회)

```bash
cd docker/sandbox
docker build -t secureops-sandbox:latest .
```

#### STEP 2. 기존 샌드박스 컨테이너 정리

```bash
# Windows CMD
for /f %i in ('docker ps -aq --filter "label=secureops=sandbox"') do docker rm -f %i

# Mac/Linux
docker rm -f $(docker ps -aq --filter "label=secureops=sandbox")
```

#### STEP 3. Gateway 서버 실행 (터미널 1)

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

확인: `✅ Docker 연결 성공` → `✅ Pool 준비 완료: 5개 대기 중`

#### STEP 4. Gateway .env 파일 설정

`gateway/.env` 파일 생성 (로컬 개발 시 필수):

```env
MODEL_PHISHING_URL=http://localhost:8001
MODEL_NETWORK_URL=http://localhost:8002
MODEL_AIOPS_URL=http://localhost:8003
JWT_SECRET=change-me-in-production
```

> ⚠️ Docker Compose 실행 시에는 이 파일 불필요 (docker-compose.yml에서 설정)

#### STEP 5. Model-Phishing 서버 실행 (터미널 2)

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

확인: `✅ 모델 로딩 완료: RandomForestClassifier (피처 18개)`

> ⚠️ `phishing_ml_model.pkl` 파일이 `model-phishing/app/ml/` 안에 있어야 함

#### STEP 6. Frontend 실행 (터미널 3)

```bash
cd frontend
npm install    # 최초 1회
npm run dev
```

> 포트 3000이 예약된 경우: `npx vite --host 0.0.0.0 --port 5173`

#### STEP 7. 접속 및 테스트

| 서비스 | URL |
|--------|-----|
| 대시보드 | http://localhost:3000 (또는 5173) |
| Gateway Swagger | http://localhost:8000/docs |
| Model-Phishing Swagger | http://localhost:8001/docs |

로그인 → URL 검사 → 샌드박스 모드 순서로 테스트.

### 방법 2: Docker Compose 통합 실행

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

서비스별 접속 주소:

| 서비스 | URL |
|--------|-----|
| Gateway API | http://localhost:8000/docs |
| Model 1 - Phishing | http://localhost:8001/docs |
| Model 2 - Network | http://localhost:8002/docs |
| Model 3 - AIOps | http://localhost:8003/docs |
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
   ├─ Model 2: 네트워크 트래픽 실시간 분석 (자동)
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
| `/api/sandbox/assign` | POST | ✅ | 샌드박스 컨테이너 할당 |
| `/api/sandbox/release/{id}` | POST | ✅ | 세션 종료 + 컨테이너 삭제 |
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

## 개발 규칙

### 코드 구조 원칙 (스파게티 방지)

1. **라우터에 로직 금지** — 라우터는 요청 수신 + 응답 반환만. 로직은 services/에 위임.
2. **서비스 간 직접 호출 금지** — 필요하면 라우터에서 조합.
3. **데이터는 스키마로만** — 모든 요청/응답은 schemas/의 Pydantic 모델을 통과.
4. **모델 서버 독립성** — 각 모델 서버는 Gateway를 import하지 않음. HTTP API로만 통신.

### Git 브랜치 전략

```
main              ← 배포 가능 상태만
├── develop       ← 통합 개발 브랜치
│   ├── feat/screening-server
│   ├── feat/sandbox-network-collector
│   ├── feat/interceptor
│   ├── feat/model2-network       (서용준)
│   ├── feat/model3-aiops         (차인택)
│   └── feat/frontend-upgrade     (김태호)
```

### 프로토타입 계정 (개발용)

| 계정 | 비밀번호 | 역할 | 비고 |
|------|----------|------|------|
| `user` | `user123` | 일반 사용자 | Model 1, 2 상태만 표시 |
| `admin` | `admin123` | 관리자 | Model 3 + Pool 관리 + 리소스 모니터링 |

> ⚠️ 프로토타입 전용. 프로덕션에서는 DB 기반 인증으로 교체.

---

## 역할 분배

| 이름 | 역할 | 담당 영역 | 작업 디렉토리 |
|------|------|-----------|---------------|
| 이종구 | PM / 백엔드 | Gateway, Model 1, Screening, Docker 인프라, 인터셉터 | `gateway/`, `model-phishing/`, `model-screening/`, `interceptor/` |
| 서용준 | AI 모델링 | Model 2 (네트워크 로그 분석) | `model-network/` |
| 차인택 | AIOps | Model 3 (리소스 이상 탐지 + Ollama RAG) | `model-aiops/` |
| 김태호 | 프론트엔드 | React 대시보드, Firebase | `frontend/` |

### 팀원 작업 가이드

각 모델 서버는 동일한 패턴. 자기 디렉토리 안에서만 작업하면 됩니다.

**필수 구현 엔드포인트:**

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/health` | GET | Gateway 헬스체크용. `{"status": "ok"}` 반환 |
| `/predict` | POST | 추론. 입력/출력은 `gateway/app/schemas/` 참고 |

**팀원 작업 순서:**
1. 자기 모델 디렉토리에서 가상환경 생성 + 의존성 설치
2. `app/services/`에 추론 로직 구현
3. `app/routers/`에 엔드포인트 연결
4. `/health`, `/predict` 정상 동작 확인
5. Gateway와 연동 테스트

**입력/출력 예시 (2번 모델):**

```json
// POST /predict 요청
{
  "sandbox_id": "abc123",
  "log_data": {
    "packet_count": 150,
    "bytes_sent": 24000,
    "bytes_received": 180000,
    "request_frequency": 12.5,
    "domain_length": 28,
    "ttl": 64,
    "protocol": "HTTPS"
  }
}

// 응답
{
  "is_malicious": false,
  "confidence": 0.15,
  "threat_type": null,
  "details": null
}
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| Backend | FastAPI, PostgreSQL, Redis, Celery |
| AI/ML | scikit-learn (RandomForest), XGBoost, LightGBM, LSTM, Isolation Forest |
| AIOps | Prometheus, cAdvisor, Ollama, ChromaDB |
| Sandbox | Docker SDK (docker-py), noVNC, Chromium, Xvfb, x11vnc |
| Interceptor | mitmproxy, pystray, Tkinter |
| Infra | Docker Compose |
| MLOps | GitHub CI/CD, WandB |
| Frontend | React, TypeScript, Tailwind CSS, Vite, Recharts, Lucide Icons |

---

## 트러블슈팅

### 자주 발생하는 문제

| 문제 | 원인 | 해결 |
|------|------|------|
| `getaddrinfo failed` | 모델 서버 URL이 Docker 호스트명 | `gateway/.env`에서 `localhost`로 변경 |
| 토큰 만료 (401) | JWT 60분 만료 | 로그아웃 후 재로그인 |
| 포트 3000 사용 불가 | Hyper-V 포트 예약 | `npx vite --host 0.0.0.0 --port 5173` |
| Chromium FATAL (Docker) | snap 문제 (Ubuntu) | Debian 기반 이미지 사용 |
| noVNC 검은 화면 | Chromium 크래시 | `docker logs` 확인, autorestart=false 설정 |
| 샌드박스 포트 불일치 | Pool 포트 카운터 꼬임 | 컨테이너 전부 정리 후 Gateway 재시작 |
| 모델 더미 응답 | pkl 파일 누락 | `phishing_ml_model.pkl`을 `ml/` 폴더에 복사 |
| gcloud 인증 오류 | Docker 이미지 pull 실패 | `gcloud auth login` → `gcloud auth configure-docker` |
