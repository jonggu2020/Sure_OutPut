"""
시스템 트레이
============
대시보드 열기, 로그아웃, 종료.
"""

import pystray
from PIL import Image, ImageDraw
import webbrowser

from interceptor.client import gateway_client


def _create_icon(color: str = "#22C55E") -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill="#1E293B")
    draw.ellipse([18, 18, 46, 46], fill=color)
    return img


def create_tray(on_logout_callback=None, on_quit_callback=None):
    icon_color = "#22C55E"
    status_text = "보호 중 ✓"

    def on_dashboard(icon, item):
        # 대시보드 열기 (토큰 포함)
        token = gateway_client.token
        dashboard = gateway_client.dashboard_url
        if token:
            webbrowser.open(f"{dashboard}/login?token={token}")
        else:
            webbrowser.open(dashboard)

    def on_logout(icon, item):
        gateway_client.logout()
        icon.stop()
        if on_logout_callback:
            on_logout_callback()

    def on_quit(icon, item):
        icon.stop()
        if on_quit_callback:
            on_quit_callback()

    icon = pystray.Icon(
        name="SecureOps",
        icon=_create_icon(icon_color),
        title=f"SecureOps — {status_text}",
        menu=pystray.Menu(
            pystray.MenuItem(f"상태: {status_text}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("대시보드 열기", on_dashboard),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("로그아웃", on_logout),
            pystray.MenuItem("종료", on_quit),
        ),
    )

    return icon
