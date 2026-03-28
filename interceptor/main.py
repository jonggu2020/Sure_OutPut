"""
SecureOps Interceptor
=====================
사용자 PC에서 실행되는 경량 프록시 에이전트.
브라우저의 URL 요청을 가로채 Gateway 서버로 전송.

구성:
- proxy.py     → mitmproxy 기반 로컬 프록시
- client.py    → Gateway API 통신 클라이언트
- tray.py      → 시스템 트레이 UI (pystray)
- alert.py     → 위험 감지 시 팝업 알림
"""

import threading
import sys

from interceptor.tray import start_tray
from interceptor.proxy import start_proxy


def main():
    """인터셉터 시작. 프록시와 트레이를 별도 스레드로 실행."""
    # 프록시 서버 (백그라운드 스레드)
    proxy_thread = threading.Thread(target=start_proxy, daemon=True)
    proxy_thread.start()

    # 시스템 트레이 (메인 스레드)
    start_tray()


if __name__ == "__main__":
    main()
