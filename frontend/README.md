# SecureOps Frontend

> 담당: 김태호 | React + TypeScript + Tailwind CSS

---

## 실행 방법

```bash
cd frontend
npm install
npm run dev
```

> 포트 3000이 예약된 경우: `npx vite --host 0.0.0.0 --port 5173`

---

## 현재 구현된 페이지

| 페이지 | 경로 | 설명 |
|--------|------|------|
| LoginPage | /login | JWT 로그인 (user/admin 구분) |
| DashboardPage | / | 헬스체크 신호등 (녹/주황/적) |
| ScanPage | /scan | URL 검사 + 샌드박스 진입 |
| SandboxPage | /sandbox | noVNC 원격 브라우저 |
| AdminPage | /admin | Pool 관리 + 리소스 모니터링 (admin 전용) |

---

## API 통신

모든 API 호출은 `src/services/api.ts`에서 관리.
Vite 프록시가 `/api` 요청을 `localhost:8000`으로 전달.

```typescript
// vite.config.ts
proxy: {
  "/api": {
    target: "http://localhost:8000",
  },
}
```

---

## 기술 스택

- React 18 + TypeScript
- Tailwind CSS (다크 테마)
- Vite (빌드)
- Recharts (차트)
- Lucide React (아이콘)

---

## 주요 파일

| 파일 | 설명 |
|------|------|
| src/services/api.ts | Gateway API 클라이언트 (모든 통신) |
| src/contexts/AuthContext.tsx | 로그인 상태 관리 |
| src/components/Layout.tsx | 사이드바 (admin 메뉴 조건부) |

---

## 역할별 화면 차이

| 기능 | user | admin |
|------|------|-------|
| 대시보드 | Model 1, 2 상태 | Model 1, 2, 3 상태 |
| URL 검사 | ✅ | ✅ |
| 샌드박스 | ✅ | ✅ |
| 관리자 메뉴 | ❌ 안 보임 | ✅ Pool 관리 + 리소스 |
