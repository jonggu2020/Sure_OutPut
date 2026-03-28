"""
샌드박스 서비스
==============
사용자 → 샌드박스 할당/반환.
관리자 → Pool 관리, 리소스 모니터링.
sandbox_pool과 분리하여 결합도 최소화.
"""

from app.services.sandbox_pool import sandbox_pool
from app.schemas.sandbox import (
    SandboxAssignResponse,
    PoolStatus,
    PoolConfigUpdate,
    ServerResources,
)


class SandboxService:
    """샌드박스 관련 비즈니스 로직."""

    async def assign_sandbox(self, user_id: str, url: str) -> SandboxAssignResponse | None:
        """사용자에게 샌드박스 컨테이너 할당."""
        info = await sandbox_pool.assign(user_id, url)
        if not info:
            return None

        return SandboxAssignResponse(
            sandbox_id=info.container_id,
            novnc_url=info.novnc_url,
            target_url=url,
            status="assigned",
        )

    async def release_sandbox(self, container_id: str):
        """사용자 세션 종료 → 컨테이너 삭제."""
        await sandbox_pool.release(container_id)

    def get_pool_status(self) -> PoolStatus:
        """관리자용 Pool 상태 조회."""
        return sandbox_pool.get_pool_status()

    async def update_pool_config(self, config: PoolConfigUpdate):
        """관리자/AIOps가 Pool 설정 변경."""
        await sandbox_pool.update_config(
            pool_size=config.pool_size,
            cpu_limit=config.default_cpu_limit,
            memory_limit=config.default_memory_limit,
        )

    async def force_remove_container(self, container_id: str) -> bool:
        """관리자가 특정 컨테이너 강제 삭제."""
        return await sandbox_pool.force_remove(container_id)

    def get_server_resources(self) -> ServerResources:
        """서버 리소스 상태 조회."""
        return sandbox_pool.get_server_resources()


sandbox_service = SandboxService()
