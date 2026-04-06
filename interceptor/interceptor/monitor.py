"""
브라우저 URL 감시기
==================
브라우저 활성 탭 URL이 변경될 때만 Gateway에 검사 요청.
"""

import time
import re
import ctypes
import ctypes.wintypes
import subprocess

from interceptor.client import gateway_client


class URLMonitor:

    BROWSER_NAMES = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe"}

    def __init__(self, poll_interval: float = 1.0):
        self.poll_interval = poll_interval
        self.running = True
        self.last_url = ""
        self._checked_cache: dict[str, dict] = {}
        self._cache_ttl = 60

        self.on_result = None  # 모든 검사 결과 콜백 (정상+비정상)

    def start(self):
        print(f"🔍 브라우저 URL 감시 시작")

        while self.running:
            try:
                url = self._get_active_browser_url()

                if url and url != self.last_url:
                    self.last_url = url
                    self._check_url(url)

            except Exception:
                pass

            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False

    def _get_active_browser_url(self) -> str | None:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return None

            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return None

            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

            pid = ctypes.wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            process_name = self._get_process_name(pid.value)
            if process_name and process_name.lower() in self.BROWSER_NAMES:
                url = self._read_url_from_address_bar()
                return url

        except Exception:
            pass
        return None

    def _get_process_name(self, pid: int) -> str | None:
        try:
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
            )
            if not handle:
                return None
            buf = ctypes.create_unicode_buffer(260)
            size = ctypes.wintypes.DWORD(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                handle, 0, buf, ctypes.byref(size)
            )
            ctypes.windll.kernel32.CloseHandle(handle)
            path = buf.value
            if path:
                return path.split("\\")[-1]
        except Exception:
            pass
        return None

    def _read_url_from_address_bar(self) -> str | None:
        try:
            ps_script = '''
            Add-Type -AssemblyName UIAutomationClient
            $root = [System.Windows.Automation.AutomationElement]::FocusedElement
            $walker = [System.Windows.Automation.TreeWalker]::RawViewWalker

            function Find-AddressBar($element, $depth) {
                if ($depth -gt 8) { return $null }
                $child = $walker.GetFirstChild($element)
                while ($child -ne $null) {
                    $controlType = $child.Current.ControlType
                    if ($controlType -eq [System.Windows.Automation.ControlType]::Edit) {
                        try {
                            $pattern = $child.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern)
                            $value = $pattern.Current.Value
                            if ($value -match "^https?://" -or $value -match "^[a-zA-Z0-9].*\\.") {
                                Write-Output $value
                                return
                            }
                        } catch {}
                    }
                    Find-AddressBar $child ($depth + 1)
                    $child = $walker.GetNextSibling($child)
                }
            }

            $desktop = [System.Windows.Automation.AutomationElement]::RootElement
            $focused = [System.Windows.Automation.AutomationElement]::FocusedElement
            $parent = $walker.GetParent($focused)
            while ($parent -ne $null -and $parent -ne $desktop) {
                $prev = $parent
                $parent = $walker.GetParent($parent)
            }
            if ($prev) { Find-AddressBar $prev 0 }
            '''

            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=3,
            )
            url = result.stdout.strip()
            if url:
                if not url.startswith("http"):
                    url = "https://" + url
                return url
        except Exception:
            pass
        return None

    def _check_url(self, url: str):
        # 내부 주소 스킵
        if any(x in url for x in ["localhost", "127.0.0.1", "192.168.", "chrome://", "edge://", "about:"]):
            return

        # 도메인 추출
        domain_match = re.search(r'https?://([^/]+)', url)
        domain = domain_match.group(1) if domain_match else url

        # 캐시 확인
        now = time.time()
        if domain in self._checked_cache:
            cached = self._checked_cache[domain]
            if now - cached.get("time", 0) < self._cache_ttl:
                return

        print(f"   🔎 검사: {url[:60]}...")

        result = gateway_client.check_url(url)
        if result is None:
            return

        # 캐시 저장
        self._checked_cache[domain] = {
            "time": now,
            "risk_level": result.get("risk_level", "safe"),
        }

        risk_level = result.get("risk_level", "safe")
        print(f"   {'✅ 안전' if risk_level == 'safe' else '🚨 위험'}: {domain}")

        # 모든 결과 콜백 (정상 포함)
        if self.on_result:
            self.on_result(url, result)
