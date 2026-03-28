"""
로컬 프록시
==========
mitmproxy를 활용한 HTTP/HTTPS 트래픽 가로채기.
브라우저 요청 → URL 추출 → Gateway 검사 → 통과/차단 결정.
"""

import asyncio
from mitmproxy import http, options
from mitmproxy.tools.dump import DumpMaster

from interceptor.client import gateway_client
from interceptor.alert import show_alert


class PhishingInterceptor:
    """mitmproxy addon: 모든 HTTP 요청을 가로채서 검사."""

    def __init__(self):
        self.loop = asyncio.new_event_loop()
        # 검사 제외 도메인 (내부 서버, CDN 등)
        self.skip_domains = {
            "localhost",
            "127.0.0.1",
            "secureops.local",
            "cdn.jsdelivr.net",
            "fonts.googleapis.com",
            "fonts.gstatic.com",
        }
        # 검사 제외 확장자 (정적 리소스)
        self.skip_extensions = {
            ".css", ".js", ".png", ".jpg", ".jpeg", ".gif",
            ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot",
        }

    def request(self, flow: http.HTTPFlow) -> None:
        """모든 HTTP 요청에서 호출됨."""
        url = flow.request.pretty_url
        host = flow.request.pretty_host

        # 정적 리소스 및 내부 도메인 스킵
        if self._should_skip(host, url):
            return

        # Gateway에 URL 검사 요청
        try:
            result = self.loop.run_until_complete(
                gateway_client.check_url(url)
            )

            risk_level = result.get("risk_level", "safe")

            if risk_level == "danger":
                # 위험: 요청 차단 + 알림 팝업
                user_choice = show_alert(url, result)
                if user_choice == "cancel":
                    flow.response = http.Response.make(
                        403,
                        b"<h1>SecureOps: Blocked</h1><p>Phishing detected.</p>",
                        {"Content-Type": "text/html"},
                    )
                elif user_choice == "sandbox":
                    # TODO: 샌드박스 모드로 전환
                    flow.response = http.Response.make(
                        302, b"",
                        {"Location": "http://localhost:3000/sandbox?url=" + url.encode()},
                    )
                # user_choice == "force" → 그냥 통과

            elif risk_level == "warning":
                # 주의: 알림만 표시, 통과는 허용
                show_alert(url, result)

        except Exception:
            # Gateway 연결 실패 시 그냥 통과 (가용성 우선)
            pass

    def _should_skip(self, host: str, url: str) -> bool:
        """검사 불필요한 요청인지 판별."""
        if host in self.skip_domains:
            return True
        if any(url.lower().endswith(ext) for ext in self.skip_extensions):
            return True
        return False


def start_proxy(host: str = "127.0.0.1", port: int = 8888):
    """mitmproxy 로컬 프록시 서버 시작."""
    opts = options.Options(listen_host=host, listen_port=port)
    master = DumpMaster(opts)
    master.addons.add(PhishingInterceptor())

    try:
        asyncio.run(master.run())
    except KeyboardInterrupt:
        master.shutdown()
