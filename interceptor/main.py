"""
SecureOps Interceptor v0.3
==========================
.exe 배포용. 브라우저 URL 감시 방식.

흐름:
1. 첫 실행 → 개인정보 동의
2. 로그인 (GUI)
3. 브라우저 URL 감시 (백그라운드)
4. 검사 결과 알림 팝업 (정상/비정상 모두)
5. 시스템 트레이 (대시보드/로그아웃/종료)
"""

import sys
import threading
from pathlib import Path

from interceptor.client import gateway_client, CONFIG_FILE
from interceptor.monitor import URLMonitor
from interceptor.gui import show_agreement, show_login, show_result_popup
from interceptor.tray import create_tray


AGREED_FILE = Path.home() / ".secureops" / "agreed"


def is_first_run() -> bool:
    """첫 실행 여부 (동의 파일 존재 확인)."""
    return not AGREED_FILE.exists()


def mark_agreed():
    """동의 완료 기록."""
    AGREED_FILE.parent.mkdir(parents=True, exist_ok=True)
    AGREED_FILE.write_text("agreed")


def run_app():
    """메인 앱 루프 — 로그인 → 감시 → 트레이."""

    # 서버 연결 확인
    if not gateway_client.is_connected():
        import tkinter.messagebox as mb
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        mb.showerror(
            "SecureOps",
            f"서버에 연결할 수 없습니다.\n\n서버 주소: {gateway_client.base_url}\n서버가 실행 중인지 확인하세요."
        )
        root.destroy()
        return

    # 자동 로그인 시도 (저장된 토큰)
    if not gateway_client.is_logged_in():
        if not show_login():
            return  # 로그인 취소 → 종료

    # URL 감시 시작
    monitor = URLMonitor(poll_interval=1.0)
    monitor.on_result = show_result_popup

    monitor_thread = threading.Thread(
        target=monitor.start,
        daemon=True,
    )
    monitor_thread.start()

    print("🛡 SecureOps 보호 활성화")
    print("   브라우저 URL 변경 시 자동 검사")

    # 시스템 트레이
    def on_logout():
        monitor.stop()
        print("🔓 로그아웃")
        # 로그아웃 후 다시 로그인 화면
        run_app()

    def on_quit():
        monitor.stop()
        print("👋 종료")
        sys.exit(0)

    icon = create_tray(
        on_logout_callback=on_logout,
        on_quit_callback=on_quit,
    )
    icon.run()


def main():
    """진입점."""

    # 1. 첫 실행 → 동의 화면
    if is_first_run():
        if not show_agreement():
            print("동의 거부 — 설치 취소")
            sys.exit(0)
        mark_agreed()
        print("✅ 설치 동의 완료")

    # 2. 앱 실행
    run_app()


if __name__ == "__main__":
    main()
