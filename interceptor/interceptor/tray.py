"""
시스템 트레이
============
백그라운드에서 실행되며 트레이 아이콘으로 상태 표시.
우클릭 메뉴: 상태 확인, 프록시 ON/OFF, 종료.
"""

from PIL import Image, ImageDraw
import pystray


def _create_icon_image(color: str = "green") -> Image.Image:
    """트레이 아이콘 이미지 생성 (간단한 원형)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    colors = {
        "green": (34, 197, 94),
        "orange": (245, 158, 11),
        "red": (239, 68, 68),
    }
    fill = colors.get(color, colors["green"])
    draw.ellipse([8, 8, 56, 56], fill=fill)

    return img


def start_tray():
    """시스템 트레이 시작."""

    def on_status(icon, item):
        """상태 확인."""
        # TODO: Gateway 헬스체크 호출 → 결과 표시
        pass

    def on_toggle(icon, item):
        """프록시 ON/OFF 토글."""
        # TODO: 시스템 프록시 설정 변경
        pass

    def on_quit(icon, item):
        """인터셉터 종료."""
        # TODO: 시스템 프록시 설정 원복
        icon.stop()

    icon = pystray.Icon(
        name="SecureOps",
        icon=_create_icon_image("green"),
        title="SecureOps Interceptor - Running",
        menu=pystray.Menu(
            pystray.MenuItem("상태: 실행 중", on_status, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("프록시 ON/OFF", on_toggle),
            pystray.MenuItem("종료", on_quit),
        ),
    )

    icon.run()
