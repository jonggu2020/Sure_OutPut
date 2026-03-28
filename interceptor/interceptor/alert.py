"""
알림 팝업
========
위험 URL 감지 시 사용자에게 선택지를 제공.
tkinter 기반 경량 팝업.

선택지:
- 접속 취소 (cancel)
- 강제 실행 (force)
- 샌드박스 모드 (sandbox)
"""

import tkinter as tk
from tkinter import ttk


def show_alert(url: str, scan_result: dict) -> str:
    """
    위험 알림 팝업을 띄우고 사용자 선택을 반환.

    Returns:
        "cancel" | "force" | "sandbox"
    """
    user_choice = "cancel"  # 기본값: 취소

    root = tk.Tk()
    root.title("SecureOps - 보안 경고")
    root.geometry("480x320")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    # ── 헤더 ──
    risk_level = scan_result.get("risk_level", "warning")
    confidence = scan_result.get("confidence", 0.0)

    if risk_level == "danger":
        header_color = "#ef4444"
        header_text = "위험한 사이트가 감지되었습니다"
    else:
        header_color = "#f59e0b"
        header_text = "의심스러운 사이트가 감지되었습니다"

    header_frame = tk.Frame(root, bg=header_color, height=60)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    tk.Label(
        header_frame, text=header_text,
        fg="white", bg=header_color,
        font=("맑은 고딕", 14, "bold"),
    ).pack(expand=True)

    # ── 상세 정보 ──
    info_frame = tk.Frame(root, padx=20, pady=15)
    info_frame.pack(fill="both", expand=True)

    tk.Label(
        info_frame, text=f"URL: {url[:60]}{'...' if len(url) > 60 else ''}",
        font=("맑은 고딕", 10), anchor="w", wraplength=440,
    ).pack(anchor="w", pady=(0, 5))

    tk.Label(
        info_frame, text=f"탐지 신뢰도: {confidence:.1%}",
        font=("맑은 고딕", 10), anchor="w",
    ).pack(anchor="w", pady=(0, 5))

    tk.Label(
        info_frame, text=f"위험 등급: {risk_level.upper()}",
        font=("맑은 고딕", 10, "bold"), anchor="w",
        fg=header_color,
    ).pack(anchor="w")

    # ── 버튼 ──
    btn_frame = tk.Frame(root, padx=20, pady=15)
    btn_frame.pack(fill="x")

    def on_cancel():
        nonlocal user_choice
        user_choice = "cancel"
        root.destroy()

    def on_force():
        nonlocal user_choice
        user_choice = "force"
        root.destroy()

    def on_sandbox():
        nonlocal user_choice
        user_choice = "sandbox"
        root.destroy()

    ttk.Button(btn_frame, text="접속 취소", command=on_cancel).pack(
        side="left", padx=(0, 8), expand=True, fill="x",
    )
    ttk.Button(btn_frame, text="강제 실행", command=on_force).pack(
        side="left", padx=4, expand=True, fill="x",
    )
    ttk.Button(btn_frame, text="샌드박스 모드", command=on_sandbox).pack(
        side="left", padx=(8, 0), expand=True, fill="x",
    )

    # 화면 중앙 배치
    root.update_idletasks()
    x = (root.winfo_screenwidth() - 480) // 2
    y = (root.winfo_screenheight() - 320) // 2
    root.geometry(f"+{x}+{y}")

    root.mainloop()

    return user_choice
