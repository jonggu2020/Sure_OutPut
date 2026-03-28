"""
샌드박스 스키마
==============
Docker Pool 관리 + 샌드박스 세션 관련 데이터 형태.
"""

from pydantic import BaseModel


class SandboxInfo(BaseModel):
    """개별 샌드박스 컨테이너 정보."""
    container_id: str
    status: str            # "idle" | "assigned" | "stopping"
    novnc_port: int
    novnc_url: str
    assigned_to: str | None = None   # 할당된 사용자 ID
    target_url: str | None = None    # 사용자가 접속하려는 URL
    cpu_limit: str = "0.5"           # CPU 코어 제한 (AIOps 조정 가능)
    memory_limit: str = "512m"       # 메모리 제한 (AIOps 조정 가능)


class PoolStatus(BaseModel):
    """Docker Pool 전체 상태."""
    pool_size: int          # 설정된 Pool 크기
    total: int              # 전체 컨테이너 수
    idle: int               # 대기 중
    assigned: int           # 사용 중
    containers: list[SandboxInfo]


class PoolConfigUpdate(BaseModel):
    """관리자/AIOps가 Pool 설정을 변경할 때."""
    pool_size: int | None = None           # Pool 크기 변경
    default_cpu_limit: str | None = None   # 기본 CPU 제한
    default_memory_limit: str | None = None  # 기본 메모리 제한


class SandboxAssignRequest(BaseModel):
    """사용자가 샌드박스를 요청할 때."""
    url: str


class SandboxAssignResponse(BaseModel):
    """샌드박스 할당 결과."""
    sandbox_id: str
    novnc_url: str
    target_url: str
    status: str


class ServerResources(BaseModel):
    """서버 PC 리소스 상태 (관리자 모니터링용)."""
    cpu_percent: float
    memory_percent: float
    memory_total_gb: float
    memory_used_gb: float
    disk_percent: float
    disk_total_gb: float
    disk_used_gb: float
