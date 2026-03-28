# Gateway 서버

> 담당: 이종구 | 포트: 8000 | 메인 API 서버

---

## 역할

모든 클라이언트 요청의 진입점. 인증, 라우팅, 모델 서버 통신, 샌드박스 Pool 관리를 담당합니다.

```
[프론트엔드 / 인터셉터]
    └─ Gateway (이 서버)
         ├─ /api/auth       → JWT 인증
         ├─ /api/health     → 헬스체크 (신호등)
         ├─ /api/phishing   → 1번 모델 통신
         ├─ /api/network    → 2번 모델 통신
         ├─ /api/aiops      → 3번 모델 통신 (admin)
         └─ /api/sandbox    → Docker Pool 관리
```

---

## 실행 방법

```bash
cd gateway
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### .env 파일 (로컬 개발 시 필수)

```env
MODEL_PHISHING_URL=http://localhost:8001
MODEL_NETWORK_URL=http://localhost:8002
MODEL_AIOPS_URL=http://localhost:8003
JWT_SECRET=change-me-in-production
```

---

## 코드 구조 원칙

```
routers/   → 요청/응답만 처리. 비즈니스 로직 금지.
services/  → 비즈니스 로직. 모델 서버 HTTP 통신.
schemas/   → Pydantic 데이터 모델. dict 직접 전달 금지.
core/      → 설정, 인증, DB 연결.
```

- 라우터 → 서비스 호출 (OK)
- 서비스 → 서비스 직접 호출 (금지, 라우터에서 조합)
- 모든 데이터는 schemas/ 통과

---

## 주요 파일

| 파일 | 설명 |
|------|------|
| app/main.py | 앱 진입점, 라우터 등록, Pool 초기화 |
| app/core/config.py | 환경변수 관리 |
| app/core/security.py | JWT 생성/검증, 역할 체크 |
| app/services/sandbox_pool.py | Docker Pool 핵심 로직 |
| app/routers/sandbox.py | 샌드박스 할당/반환 + 네트워크 데이터 수신 |

---

## 프로토타입 계정

| 계정 | 비밀번호 | 역할 |
|------|----------|------|
| user | user123 | 일반 사용자 |
| admin | admin123 | 관리자 |
