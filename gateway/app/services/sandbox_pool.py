"""
샌드박스 Pool 관리
==================
서버 시작 시 Docker 컨테이너를 미리 생성해두고 (Warm Pool),
사용자 요청 시 즉시 할당. 반환 시 삭제 후 새 컨테이너로 보충.

Pool 크기는 관리자 수동 조정 또는 AIOps 자동 조정 가능.

핵심 설계:
- 컨테이너는 name(secureops-sandbox-{port})으로 관리
- Pool 내부에서는 container_name을 키로 사용
- 사용 중인 포트를 Set으로 추적하여 충돌 방지
"""

import asyncio
import time
import docker
from docker.errors import NotFound, APIError
from typing import Optional

from app.schemas.sandbox import SandboxInfo, PoolStatus, ServerResources


class SandboxPool:
    """Docker 컨테이너 Warm Pool 관리자."""

    SANDBOX_IMAGE = "secureops-sandbox:latest"
    PORT_RANGE_START = 6081
    PORT_RANGE_END = 6200

    def __init__(self):
        self.client: Optional[docker.DockerClient] = None
        self.pool_size: int = 5
        self.default_cpu_limit: str = "0.5"
        self.default_memory_limit: str = "512m"
        # container_name → SandboxInfo (name 기반 관리)
        self.containers: dict[str, SandboxInfo] = {}
        # 사용 중인 포트 추적
        self.used_ports: set[int] = set()
        self._lock = asyncio.Lock()

    # ── 초기화/종료 ──

    async def initialize(self):
        """서버 시작 시 Docker 클라이언트 연결 + Pool 초기 생성."""
        try:
            self.client = docker.from_env()
            self.client.ping()
            print("✅ Docker 연결 성공")
        except Exception as e:
            print(f"⚠️ Docker 연결 실패: {e}")
            print("   샌드박스 기능이 제한됩니다.")
            return

        await self._cleanup_old_containers()

        print(f"🔧 샌드박스 Pool 초기화 (크기: {self.pool_size})...")
        await self._fill_pool()
        print(f"✅ Pool 준비 완료: {len(self._get_idle())}개 대기 중")

    async def shutdown(self):
        """서버 종료 시 모든 샌드박스 컨테이너 정리."""
        print("🧹 샌드박스 Pool 정리 중...")
        for name in list(self.containers.keys()):
            await self._remove_container(name)
        print("✅ Pool 정리 완료")

    # ── 사용자용 ──

    async def assign(self, user_id: str, target_url: str) -> Optional[SandboxInfo]:
        """대기 중인 컨테이너를 사용자에게 할당."""
        async with self._lock:
            idle = self._get_idle()
            if not idle:
                info = await self._create_container()
                if not info:
                    return None
                idle = [info]

            container = idle[0]
            container.status = "assigned"
            container.assigned_to = user_id
            container.target_url = target_url

            # 할당된 컨테이너 정보 로그
            print(f"📌 샌드박스 할당: {container.container_id} → port {container.novnc_port} → user {user_id}")

        # Chromium에서 사용자 URL 열기
        await self._open_url_in_sandbox(container.container_id, target_url)

        # Pool 보충 (백그라운드)
        asyncio.create_task(self._fill_pool())

        return container

    async def release(self, container_id: str):
        """사용자 세션 종료 → 컨테이너 삭제 → Pool 보충."""
        async with self._lock:
            # container_id로 해당 컨테이너 name 찾기
            target_name = None
            for name, info in self.containers.items():
                if info.container_id == container_id:
                    target_name = name
                    break

            if target_name:
                print(f"🔓 샌드박스 반환: {container_id} → 삭제")
                await self._remove_container(target_name)

        asyncio.create_task(self._fill_pool())

    # ── 관리자용 ──

    def get_pool_status(self) -> PoolStatus:
        idle = self._get_idle()
        assigned = self._get_assigned()
        return PoolStatus(
            pool_size=self.pool_size,
            total=len(self.containers),
            idle=len(idle),
            assigned=len(assigned),
            containers=list(self.containers.values()),
        )

    async def update_config(self, pool_size: int | None = None,
                            cpu_limit: str | None = None,
                            memory_limit: str | None = None):
        if cpu_limit:
            self.default_cpu_limit = cpu_limit
        if memory_limit:
            self.default_memory_limit = memory_limit

        if pool_size is not None and pool_size != self.pool_size:
            old_size = self.pool_size
            self.pool_size = max(1, pool_size)
            print(f"🔧 Pool 크기 변경: {old_size} → {self.pool_size}")

            if self.pool_size > old_size:
                await self._fill_pool()
            else:
                await self._shrink_pool()

    async def force_remove(self, container_id: str) -> bool:
        async with self._lock:
            target_name = None
            for name, info in self.containers.items():
                if info.container_id == container_id:
                    target_name = name
                    break
            if target_name:
                await self._remove_container(target_name)
                return True
        return False

    def get_server_resources(self) -> ServerResources:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return ServerResources(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_total_gb=round(mem.total / (1024 ** 3), 2),
            memory_used_gb=round(mem.used / (1024 ** 3), 2),
            disk_percent=disk.percent,
            disk_total_gb=round(disk.total / (1024 ** 3), 2),
            disk_used_gb=round(disk.used / (1024 ** 3), 2),
        )

    # ── 내부 메서드 ──

    def _get_idle(self) -> list[SandboxInfo]:
        return [c for c in self.containers.values() if c.status == "idle"]

    def _get_assigned(self) -> list[SandboxInfo]:
        return [c for c in self.containers.values() if c.status == "assigned"]

    def _find_available_port(self) -> Optional[int]:
        """사용 중이지 않은 포트를 찾아 반환."""
        for port in range(self.PORT_RANGE_START, self.PORT_RANGE_END):
            if port not in self.used_ports:
                return port
        return None

    async def _fill_pool(self):
        if not self.client:
            return
        idle_count = len(self._get_idle())
        needed = self.pool_size - idle_count
        for _ in range(needed):
            await self._create_container()

    async def _shrink_pool(self):
        idle = self._get_idle()
        excess = len(idle) - self.pool_size
        for i in range(excess):
            if i < len(idle):
                # name으로 찾기
                for name, info in self.containers.items():
                    if info.container_id == idle[i].container_id:
                        await self._remove_container(name)
                        break

    async def _create_container(self) -> Optional[SandboxInfo]:
        """새 샌드박스 Docker 컨테이너 생성."""
        if not self.client:
            return None

        port = self._find_available_port()
        if port is None:
            print("⚠️ 사용 가능한 포트 없음")
            return None

        container_name = f"secureops-sandbox-{port}"

        # 혹시 같은 이름이 Docker에 남아있으면 제거
        try:
            existing = self.client.containers.get(container_name)
            existing.remove(force=True)
        except NotFound:
            pass
        except Exception:
            pass

        try:
            container = self.client.containers.run(
                self.SANDBOX_IMAGE,
                detach=True,
                remove=False,
                name=container_name,
                ports={"6080/tcp": port},
                nano_cpus=int(float(self.default_cpu_limit) * 1e9),
                mem_limit=self.default_memory_limit,
                labels={
                    "secureops": "sandbox",
                    "secureops.pool": "true",
                },
                environment={
                    "VNC_RESOLUTION": "1280x720",
                    "SANDBOX_ID": container_name,
                    "GATEWAY_URL": "http://host.docker.internal:8000",
                },
            )

            # 포트를 사용 중으로 등록
            self.used_ports.add(port)

            info = SandboxInfo(
                container_id=container.short_id,
                status="idle",
                novnc_port=port,
                novnc_url=f"http://localhost:{port}/vnc_lite.html?autoconnect=true&resize=scale",
                cpu_limit=self.default_cpu_limit,
                memory_limit=self.default_memory_limit,
            )
            self.containers[container_name] = info
            print(f"   ✓ 컨테이너 생성: {container_name} (id: {container.short_id}) → port {port}")
            return info

        except Exception as e:
            print(f"⚠️ 컨테이너 생성 실패 (port {port}): {e}")
            return None

    async def _remove_container(self, container_name: str):
        """컨테이너 삭제 (데이터 완전 소멸 → 보안)."""
        if not self.client:
            return

        info = self.containers.get(container_name)

        # Docker에서 실제 삭제
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove(force=True)
        except (NotFound, APIError):
            pass
        except Exception as e:
            print(f"⚠️ 컨테이너 삭제 실패 ({container_name}): {e}")

        # 포트 해제 + Pool에서 제거
        if info:
            self.used_ports.discard(info.novnc_port)
            print(f"   ✗ 컨테이너 삭제: {container_name} → port {info.novnc_port} 해제")
        self.containers.pop(container_name, None)

    async def _open_url_in_sandbox(self, container_id: str, url: str):
        """샌드박스 컨테이너의 Chromium에서 특정 URL을 열기."""
        if not self.client:
            return
        try:
            # container_id로 name 찾기
            target_name = None
            for name, info in self.containers.items():
                if info.container_id == container_id:
                    target_name = name
                    break

            if not target_name:
                return

            container = self.client.containers.get(target_name)
            # 기존 Chromium 종료 후 URL과 함께 재시작
            container.exec_run("pkill -f chromium", detach=True)
            time.sleep(1)
            container.exec_run(
                f'chromium --no-sandbox --disable-gpu --disable-software-rasterizer '
                f'--disable-dev-shm-usage --no-first-run --start-maximized '
                f'--window-size=1280,720 "{url}"',
                detach=True,
                environment={"DISPLAY": ":1", "HOME": "/root"},
            )
            print(f"   🌐 URL 열기: {target_name} → {url[:50]}...")
        except Exception as e:
            print(f"⚠️ URL 열기 실패 ({container_id}): {e}")

    async def _cleanup_old_containers(self):
        """서버 재시작 시 이전 세션의 샌드박스 컨테이너 정리."""
        if not self.client:
            return
        try:
            old = self.client.containers.list(
                all=True,
                filters={"label": "secureops=sandbox"},
            )
            for c in old:
                try:
                    c.stop(timeout=3)
                    c.remove(force=True)
                except Exception:
                    pass
            if old:
                print(f"🧹 이전 샌드박스 {len(old)}개 정리 완료")
        except Exception:
            pass

        # 포트 추적 초기화
        self.used_ports.clear()
        self.containers.clear()


# 싱글톤 인스턴스
sandbox_pool = SandboxPool()
