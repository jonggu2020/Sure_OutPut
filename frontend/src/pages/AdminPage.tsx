import { useState, useEffect } from "react";
import {
  fetchPoolStatus, updatePoolConfig, forceRemoveContainer,
  fetchServerResources,
  type PoolStatus, type ServerResources,
} from "../services/api";
import {
  Cpu, HardDrive, MemoryStick, Monitor, RefreshCw, Trash2,
  Settings, Box, Loader2,
} from "lucide-react";

export default function AdminPage() {
  const [pool, setPool] = useState<PoolStatus | null>(null);
  const [resources, setResources] = useState<ServerResources | null>(null);
  const [loading, setLoading] = useState(true);
  const [newPoolSize, setNewPoolSize] = useState<number>(5);
  const [updating, setUpdating] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [poolData, resourceData] = await Promise.all([
        fetchPoolStatus(),
        fetchServerResources(),
      ]);
      setPool(poolData);
      setResources(resourceData);
      setNewPoolSize(poolData.pool_size);
    } catch (err) {
      console.error("데이터 로드 실패:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  async function handleUpdatePoolSize() {
    setUpdating(true);
    try {
      await updatePoolConfig({ pool_size: newPoolSize });
      await refresh();
    } catch (err) {
      console.error("Pool 설정 변경 실패:", err);
    } finally {
      setUpdating(false);
    }
  }

  async function handleRemove(containerId: string) {
    if (!confirm(`컨테이너 ${containerId}를 강제 삭제하시겠습니까?`)) return;
    try {
      await forceRemoveContainer(containerId);
      await refresh();
    } catch (err) {
      console.error("컨테이너 삭제 실패:", err);
    }
  }

  function resourceBar(percent: number) {
    const color = percent > 80 ? "bg-red-500" : percent > 60 ? "bg-amber-500" : "bg-green-500";
    return (
      <div className="w-full bg-surface-tertiary rounded-full h-2 mt-2">
        <div className={`${color} h-2 rounded-full transition-all duration-500`} style={{ width: `${percent}%` }} />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">관리자 패널</h2>
          <p className="text-gray-500 text-sm mt-1">Docker Pool 관리 · 서버 리소스 모니터링</p>
        </div>
        <button onClick={refresh} disabled={loading} className="p-2 rounded-xl hover:bg-surface-tertiary transition-colors disabled:opacity-50">
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* 서버 리소스 */}
      {resources && (
        <div>
          <h3 className="text-lg font-semibold mb-4">서버 리소스</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <Cpu size={18} className="text-blue-400" />
                <span className="text-sm font-medium">CPU</span>
                <span className="ml-auto text-xl font-bold font-mono">{resources.cpu_percent}%</span>
              </div>
              {resourceBar(resources.cpu_percent)}
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <MemoryStick size={18} className="text-purple-400" />
                <span className="text-sm font-medium">메모리</span>
                <span className="ml-auto text-xl font-bold font-mono">{resources.memory_percent}%</span>
              </div>
              {resourceBar(resources.memory_percent)}
              <p className="text-xs text-gray-500 mt-2">{resources.memory_used_gb} / {resources.memory_total_gb} GB</p>
            </div>

            <div className="card">
              <div className="flex items-center gap-3 mb-3">
                <HardDrive size={18} className="text-amber-400" />
                <span className="text-sm font-medium">디스크</span>
                <span className="ml-auto text-xl font-bold font-mono">{resources.disk_percent}%</span>
              </div>
              {resourceBar(resources.disk_percent)}
              <p className="text-xs text-gray-500 mt-2">{resources.disk_used_gb} / {resources.disk_total_gb} GB</p>
            </div>
          </div>
        </div>
      )}

      {/* Pool 설정 */}
      {pool && (
        <div>
          <h3 className="text-lg font-semibold mb-4">Docker Pool 관리</h3>

          {/* Pool 요약 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="card text-center">
              <p className="text-3xl font-bold font-mono text-brand-500">{pool.pool_size}</p>
              <p className="text-xs text-gray-500 mt-1">설정 크기</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold font-mono text-green-400">{pool.idle}</p>
              <p className="text-xs text-gray-500 mt-1">대기 중</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold font-mono text-amber-400">{pool.assigned}</p>
              <p className="text-xs text-gray-500 mt-1">사용 중</p>
            </div>
            <div className="card text-center">
              <p className="text-3xl font-bold font-mono">{pool.total}</p>
              <p className="text-xs text-gray-500 mt-1">전체</p>
            </div>
          </div>

          {/* Pool 크기 조정 */}
          <div className="card border border-brand-500/20 bg-brand-600/5 mb-6">
            <div className="flex items-center gap-4">
              <Settings size={18} className="text-brand-500" />
              <span className="text-sm font-medium">Pool 크기 조정</span>
              <input
                type="number"
                min={1}
                max={20}
                value={newPoolSize}
                onChange={(e) => setNewPoolSize(Number(e.target.value))}
                className="input-field w-24 text-center font-mono"
              />
              <button
                onClick={handleUpdatePoolSize}
                disabled={updating || newPoolSize === pool.pool_size}
                className="btn-primary text-sm disabled:opacity-50 flex items-center gap-2"
              >
                {updating ? <Loader2 size={14} className="animate-spin" /> : null}
                적용
              </button>
              <span className="text-xs text-gray-500 ml-auto">AIOps 자동 조정 예정</span>
            </div>
          </div>

          {/* 컨테이너 목록 */}
          <div className="card p-0">
            <div className="px-5 py-4 border-b border-gray-800/50">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                <Box size={16} />
                컨테이너 목록
              </h4>
            </div>

            {pool.containers.length === 0 ? (
              <div className="text-center py-8 text-gray-500 text-sm">컨테이너가 없습니다</div>
            ) : (
              <div className="divide-y divide-gray-800/50">
                {pool.containers.map((c) => (
                  <div key={c.container_id} className="px-5 py-3 flex items-center gap-4">
                    <div className={`status-dot ${c.status === "idle" ? "bg-green-500" : c.status === "assigned" ? "bg-amber-500" : "bg-red-500"}`} />

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-mono">{c.container_id}</p>
                      <p className="text-xs text-gray-500">
                        :{c.novnc_port} · CPU {c.cpu_limit} · MEM {c.memory_limit}
                        {c.assigned_to && ` · 사용자: ${c.assigned_to}`}
                      </p>
                    </div>

                    <span className={`text-xs font-mono px-2 py-0.5 rounded-md ${
                      c.status === "idle" ? "bg-green-500/15 text-green-400" :
                      c.status === "assigned" ? "bg-amber-500/15 text-amber-400" :
                      "bg-red-500/15 text-red-400"
                    }`}>
                      {c.status}
                    </span>

                    <button
                      onClick={() => handleRemove(c.container_id)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-colors"
                      title="강제 삭제"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
