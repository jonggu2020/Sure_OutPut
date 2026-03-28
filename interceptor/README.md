# SecureOps Interceptor

> 담당: 이종구 | 사용자 PC 백그라운드 에이전트

---

## 현재 상태: 🔧 뼈대만 구현

mitmproxy 기반 로컬 프록시 + 시스템 트레이 + 알림 팝업 코드 구조만 작성됨.
실제 동작은 미구현.

---

## 역할

사용자 PC에서 백그라운드로 실행. 브라우저의 모든 URL 요청을 가로채서 Screening 서버로 전송.
위험 감지 시 팝업(진행/취소/샌드박스) 표시.

```
[사용자 브라우저] → [Interceptor (로컬 프록시)]
    → Screening 서버 /quick-check
    → 의심 시 팝업 표시
    → 샌드박스 선택 시 대시보드로 리다이렉트
```

---

## 파일 구조

```
interceptor/
├── main.py                  # 진입점 (프록시 + 트레이 동시 실행)
├── interceptor/
│   ├── proxy.py             # mitmproxy 기반 URL 가로채기
│   ├── client.py            # Gateway/Screening API 통신
│   ├── alert.py             # 위험 감지 팝업 (Tkinter)
│   └── tray.py              # 시스템 트레이 아이콘 (pystray)
└── requirements.txt
```

---

## TODO

- [ ] Screening 서버 연동 (quick-check)
- [ ] 시스템 프록시 자동 설정
- [ ] CA 인증서 자동 설치 (HTTPS 인터셉트)
- [ ] 팝업 → 대시보드 연동
