"""
SecureOps GUI
=============
설치 동의 화면, 로그인 창, 알림 팝업.
모두 Tkinter 기반.
"""

import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser
import time

from interceptor.client import gateway_client


# ══════════════════════════════════════════════
# 1. 설치 동의 화면 (첫 실행 시)
# ══════════════════════════════════════════════

def show_agreement() -> bool:
    """개인정보 수집·이용 동의. True면 동의, False면 거부."""
    agreed = [False]

    root = tk.Tk()
    root.title("SecureOps 설치")
    root.geometry("500x520")
    root.resizable(False, False)
    root.configure(bg="#1E293B")

    # 로고
    tk.Label(
        root, text="🛡 SecureOps",
        font=("맑은 고딕", 22, "bold"),
        bg="#1E293B", fg="#60A5FA",
    ).pack(pady=(25, 5))

    tk.Label(
        root, text="AI 기반 피싱 탐지 보안 솔루션",
        font=("맑은 고딕", 10),
        bg="#1E293B", fg="#94A3B8",
    ).pack(pady=(0, 15))

    # 동의서 텍스트
    frame = tk.Frame(root, bg="#1E293B")
    frame.pack(padx=20, fill="both", expand=True)

    text_box = tk.Text(
        frame, wrap="word", height=15,
        font=("맑은 고딕", 9),
        bg="#0F172A", fg="#CBD5E1",
        relief="flat", padx=10, pady=10,
    )
    text_box.insert("1.0", """[개인정보 수집·이용 동의서]

SecureOps는 안전한 인터넷 사용을 위해 아래 정보를 수집합니다.

1. 수집 항목
  - 브라우저 활성 탭 URL 정보
  - 네트워크 트래픽 메타데이터 (샌드박스 내)

2. 수집 목적
  - 피싱 사이트 실시간 탐지 및 차단
  - 악성 네트워크 트래픽 분석
  - 서비스 품질 개선

3. 보유 기간
  - 검사 데이터는 실시간 분석 후 즉시 삭제
  - 샌드박스 세션 종료 시 모든 데이터 완전 소멸

4. 동의 거부 시
  - 서비스 이용이 제한됩니다.

※ 본 프로그램은 선문대학교 AI소프트웨어학과
  '확실한 OutPut' 팀의 졸업 프로젝트입니다.
""")
    text_box.config(state="disabled")
    text_box.pack(fill="both", expand=True)

    # 체크박스
    agree_var = tk.BooleanVar(value=False)

    def on_check():
        install_btn.config(state="normal" if agree_var.get() else "disabled")

    tk.Checkbutton(
        root,
        text="위 내용에 동의합니다.",
        variable=agree_var,
        command=on_check,
        font=("맑은 고딕", 10),
        bg="#1E293B", fg="#E2E8F0",
        selectcolor="#334155",
        activebackground="#1E293B",
        activeforeground="#E2E8F0",
    ).pack(pady=(10, 5))

    # 버튼
    btn_frame = tk.Frame(root, bg="#1E293B")
    btn_frame.pack(pady=(5, 20))

    def on_cancel():
        root.destroy()

    def on_install():
        agreed[0] = True
        root.destroy()

    tk.Button(
        btn_frame, text="취소",
        width=12, font=("맑은 고딕", 10),
        bg="#475569", fg="white", relief="flat",
        command=on_cancel,
    ).pack(side=tk.LEFT, padx=8)

    install_btn = tk.Button(
        btn_frame, text="설치 및 동의",
        width=14, font=("맑은 고딕", 10, "bold"),
        bg="#3B82F6", fg="white", relief="flat",
        command=on_install, state="disabled",
    )
    install_btn.pack(side=tk.LEFT, padx=8)

    root.mainloop()
    return agreed[0]


# ══════════════════════════════════════════════
# 2. 로그인 화면
# ══════════════════════════════════════════════

def show_login() -> bool:
    """GUI 로그인 창. True면 로그인 성공."""
    success = [False]

    root = tk.Tk()
    root.title("SecureOps 로그인")
    root.geometry("380x340")
    root.resizable(False, False)
    root.configure(bg="#1E293B")

    # 로고
    tk.Label(
        root, text="🛡 SecureOps",
        font=("맑은 고딕", 20, "bold"),
        bg="#1E293B", fg="#60A5FA",
    ).pack(pady=(30, 5))

    tk.Label(
        root, text="로그인하여 보안 감시를 시작하세요",
        font=("맑은 고딕", 9),
        bg="#1E293B", fg="#94A3B8",
    ).pack(pady=(0, 20))

    # 입력 필드
    input_frame = tk.Frame(root, bg="#1E293B")
    input_frame.pack(padx=40)

    tk.Label(
        input_frame, text="아이디",
        font=("맑은 고딕", 9),
        bg="#1E293B", fg="#CBD5E1", anchor="w",
    ).pack(fill="x")

    username_entry = tk.Entry(
        input_frame, font=("맑은 고딕", 11),
        bg="#334155", fg="white", relief="flat",
        insertbackground="white",
    )
    username_entry.pack(fill="x", pady=(2, 10), ipady=5)

    tk.Label(
        input_frame, text="비밀번호",
        font=("맑은 고딕", 9),
        bg="#1E293B", fg="#CBD5E1", anchor="w",
    ).pack(fill="x")

    password_entry = tk.Entry(
        input_frame, font=("맑은 고딕", 11),
        bg="#334155", fg="white", relief="flat",
        insertbackground="white", show="●",
    )
    password_entry.pack(fill="x", pady=(2, 5), ipady=5)

    # 에러 메시지
    error_label = tk.Label(
        root, text="",
        font=("맑은 고딕", 9),
        bg="#1E293B", fg="#EF4444",
    )
    error_label.pack(pady=(5, 0))

    # 로그인 버튼
    def on_login(event=None):
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if not username or not password:
            error_label.config(text="아이디와 비밀번호를 입력하세요.")
            return

        if not gateway_client.is_connected():
            error_label.config(text="서버에 연결할 수 없습니다.")
            return

        if gateway_client.login(username, password):
            success[0] = True
            root.destroy()
        else:
            error_label.config(text="아이디 또는 비밀번호가 올바르지 않습니다.")

    # Enter 키 바인딩
    password_entry.bind("<Return>", on_login)
    username_entry.bind("<Return>", on_login)

    tk.Button(
        root, text="로그인",
        width=30, font=("맑은 고딕", 11, "bold"),
        bg="#3B82F6", fg="white", relief="flat",
        command=on_login,
    ).pack(pady=(10, 20))

    username_entry.focus_set()
    root.mainloop()
    return success[0]


# ══════════════════════════════════════════════
# 3. 알림 팝업 (오른쪽 하단, 모든 결과)
# ══════════════════════════════════════════════

def show_result_popup(url: str, result: dict):
    """별도 스레드에서 오른쪽 하단 알림 팝업 표시."""
    thread = threading.Thread(
        target=_create_popup,
        args=(url, result),
        daemon=True,
    )
    thread.start()


def _create_popup(url: str, result: dict):
    risk_level = result.get("risk_level", "safe")
    confidence = result.get("confidence", 0.0)

    root = tk.Tk()
    root.overrideredirect(True)  # 타이틀바 없음
    root.attributes("-topmost", True)

    # 크기 및 위치 (오른쪽 하단)
    popup_w = 380
    popup_h = 220
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = screen_w - popup_w - 20
    y = screen_h - popup_h - 60
    root.geometry(f"{popup_w}x{popup_h}+{x}+{y}")

    # 색상
    if risk_level == "safe":
        bg_color = "#1E3A2F"
        accent = "#22C55E"
        icon = "✅"
        title = "안전한 사이트"
    elif risk_level == "warning":
        bg_color = "#3B2F1E"
        accent = "#F59E0B"
        icon = "⚠️"
        title = "피싱 의심 감지"
    else:
        bg_color = "#3B1E1E"
        accent = "#EF4444"
        icon = "🚨"
        title = "피싱 위험 감지"

    root.configure(bg=bg_color)

    # 상단 바 (색상 바)
    bar = tk.Frame(root, bg=accent, height=3)
    bar.pack(fill="x")

    # 제목
    header_frame = tk.Frame(root, bg=bg_color)
    header_frame.pack(fill="x", padx=15, pady=(10, 5))

    tk.Label(
        header_frame, text=f"{icon} {title}",
        font=("맑은 고딕", 13, "bold"),
        bg=bg_color, fg=accent,
    ).pack(side="left")

    # 닫기 버튼
    close_btn = tk.Label(
        header_frame, text="✕",
        font=("맑은 고딕", 12),
        bg=bg_color, fg="#64748B", cursor="hand2",
    )
    close_btn.pack(side="right")
    close_btn.bind("<Button-1>", lambda e: root.destroy())

    # URL + 신뢰도
    display_url = url[:50] + "..." if len(url) > 50 else url
    tk.Label(
        root, text=display_url,
        font=("Consolas", 8),
        bg=bg_color, fg="#94A3B8",
    ).pack(padx=15, anchor="w")

    tk.Label(
        root,
        text=f"위험도: {risk_level.upper()}  |  신뢰도: {confidence:.1%}",
        font=("맑은 고딕", 9),
        bg=bg_color, fg="#CBD5E1",
    ).pack(padx=15, anchor="w", pady=(3, 0))

    # 버튼 3개
    btn_frame = tk.Frame(root, bg=bg_color)
    btn_frame.pack(fill="x", padx=15, pady=(12, 10))

    def on_cancel():
        root.destroy()

    def on_force():
        root.destroy()
        webbrowser.open(url)

    def on_sandbox():
        root.destroy()
        # Gateway에 직접 샌드박스 할당
        sandbox = gateway_client.assign_sandbox(url)
        if sandbox and sandbox.get("novnc_url"):
            webbrowser.open(sandbox["novnc_url"])
        else:
            messagebox.showwarning("SecureOps", "샌드박스 할당에 실패했습니다.")

    tk.Button(
        btn_frame, text="무시",
        width=8, font=("맑은 고딕", 9),
        bg="#475569", fg="white", relief="flat", cursor="hand2",
        command=on_cancel,
    ).pack(side=tk.LEFT, padx=3)

    tk.Button(
        btn_frame, text="강제 접속",
        width=10, font=("맑은 고딕", 9),
        bg="#F59E0B", fg="white", relief="flat", cursor="hand2",
        command=on_force,
    ).pack(side=tk.LEFT, padx=3)

    tk.Button(
        btn_frame, text="🛡 샌드박스",
        width=12, font=("맑은 고딕", 9, "bold"),
        bg="#3B82F6", fg="white", relief="flat", cursor="hand2",
        command=on_sandbox,
    ).pack(side=tk.LEFT, padx=3)

    # 안전한 사이트는 5초 후 자동 닫힘
    if risk_level == "safe":
        root.after(5000, root.destroy)

    root.mainloop()
