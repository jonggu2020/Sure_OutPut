# Docker Sandbox 이미지

> 격리 브라우저 환경 (noVNC + Chromium + 네트워크 수집 에이전트)

---

## 빌드 방법

```bash
cd docker/sandbox
docker build -t secureops-sandbox:latest .

# 캐시 없이 재빌드
docker build -t secureops-sandbox:latest . --no-cache
```

---

## 구성 요소

| 프로세스 | 역할 |
|---------|------|
| Xvfb | 가상 디스플레이 (1280x720) |
| x11vnc | VNC 서버 (포트 5900) |
| websockify + noVNC | 웹 기반 VNC 클라이언트 (포트 6080) |
| Chromium | 격리 브라우저 |
| network_agent.py | 네트워크 트래픽 수집 → Gateway 전송 (5초마다) |

---

## 파일 구조

```
docker/sandbox/
├── Dockerfile           # Debian 기반, Chromium + noVNC + tcpdump
├── supervisord.conf     # 프로세스 관리 (5개 프로세스)
├── start.sh             # 시작 스크립트
└── network_agent.py     # 네트워크 수집 에이전트
```

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| GATEWAY_URL | http://host.docker.internal:8000 | Gateway 주소 |
| SANDBOX_ID | 컨테이너 이름 | 샌드박스 식별자 |
| VNC_RESOLUTION | 1280x720 | 화면 해상도 |

---

## 주의사항

- Chromium은 `autorestart=false` — Gateway가 URL과 함께 exec으로 실행
- `vnc_lite.html`로 접속 (vnc.html은 UI 버그 있음)
- 컨테이너 삭제 시 모든 데이터 소멸 (보안)
