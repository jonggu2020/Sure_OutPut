# SecureOps Interceptor

> 사용자 PC 백그라운드 보안 에이전트 (.exe 배포)

---

## 역할

사용자 PC에서 백그라운드로 실행. mitmproxy 기반으로 모든 HTTP/HTTPS 요청을 가로채서 Gateway에 피싱 검사 요청. 위험 감지 시 팝업(취소/강제접속/샌드박스) 표시.

---

## 파일 구조

```
interceptor/
├── main.py                  # 진입점 (프록시 + 트레이 + 로그인)
├── build_exe.py             # PyInstaller .exe 빌드 스크립트
├── requirements.txt
└── interceptor/
    ├── setup.py             # 초기 설치 (CA 인증서 + 프록시 설정)
    ├── proxy.py             # mitmproxy 엔진 (URL 인터셉트)
    ├── client.py            # Gateway API 통신 + 토큰 관리
    ├── alert.py             # 위험 감지 팝업 (Tkinter)
    └── tray.py              # 시스템 트레이 아이콘
```

---

## 사용법

### 개발 모드

```bash
cd interceptor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 1. 초기 설치 (관리자 권한 필요 — CA 인증서 + 프록시)
python main.py --setup

# 2. 실행
python main.py

# 3. 제거 (프록시 해제)
python main.py --uninstall
```

### .exe 빌드 + 배포

```bash
python build_exe.py
# → dist/SecureOps.exe 생성
```

사용자에게 `SecureOps.exe` 배포. 최초 실행 시 `--setup` 옵션으로 설치.

---

## 동작 흐름

```
1. Gateway 서버 연결 확인
2. 로그인 (토큰 저장 → 이후 자동 로그인)
3. mitmproxy 프록시 시작 (127.0.0.1:8888)
4. 시스템 트레이 아이콘 표시
5. 브라우저 요청 가로채기 → Gateway /api/phishing/check
6. safe → 통과
7. warning/danger → 요청 차단 + 팝업
   ├─ 접속 취소
   ├─ 강제 접속 (사용자 책임)
   └─ 샌드박스 모드 (대시보드로 이동)
```
