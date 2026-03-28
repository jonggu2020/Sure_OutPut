import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { fetchHealth, type HealthData, type ModelStatus } from "../services/api";
import { Activity, Cpu, Network, Brain, RefreshCw } from "lucide-react";

const MODEL_INFO: Record<string, { label: string; icon: typeof Activity; desc: string }> = {
  phishing: {
    label: "HTML 피싱 탐지",
    icon: Brain,
    desc: "URL 및 HTML 구조 기반 피싱 판별 (Model 1)",
  },
  network: {
    label: "네트워크 로그 분석",
    icon: Network,
    desc: "샌드박스 내 네트워크 트래픽 이상 탐지 (Model 2)",
  },
  aiops: {
    label: "AIOps 리소스 모니터",
    icon: Cpu,
    desc: "Docker 리소스 이상 감지 + 자동 의사결정 (Model 3)",
  },
};

const STATUS_STYLES: Record<string, { dot: string; bg: string; text: string; label: string }> = {
  green: {
    dot: "bg-status-green shadow-lg shadow-green-500/40",
    bg: "bg-green-500/10 border-green-500/20",
    text: "text-green-400",
    label: "정상",
  },
  orange: {
    dot: "bg-status-orange shadow-lg shadow-amber-500/40",
    bg: "bg-amber-500/10 border-amber-500/20",
    text: "text-amber-400",
    label: "지연",
  },
  red: {
    dot: "bg-status-red shadow-lg shadow-red-500/40",
    bg: "bg-red-500/10 border-red-500/20",
    text: "text-red-400",
    label: "중단",
  },
};

export default function DashboardPage() {
  const { role } = useAuth();
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const data = await fetchHealth();
      setHealth(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("헬스체크 실패:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 15000); // 15초마다 갱신
    return () => clearInterval(interval);
  }, []);

  const visibleModels = health
    ? Object.entries(health.models).filter(
        ([, v]) => !v.admin_only || role === "admin"
      )
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">대시보드</h2>
          <p className="text-gray-500 text-sm mt-1">
            SecureOps 플랫폼 실시간 상태
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastUpdated && (
            <span className="text-xs text-gray-600 font-mono">
              {lastUpdated.toLocaleTimeString("ko-KR")} 갱신
            </span>
          )}
          <button
            onClick={refresh}
            disabled={loading}
            className="p-2 rounded-xl hover:bg-surface-tertiary transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
          </button>
        </div>
      </div>

      {/* Gateway status */}
      <div className="card flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-brand-600/15 rounded-xl flex items-center justify-center">
            <Activity size={22} className="text-brand-500" />
          </div>
          <div>
            <h3 className="font-semibold">Gateway Server</h3>
            <p className="text-sm text-gray-500">메인 API 서버 · 인증 · 라우팅</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="status-dot bg-status-green shadow-lg shadow-green-500/40" />
          <span className="text-sm text-green-400 font-medium">
            {health?.gateway || "확인 중..."}
          </span>
        </div>
      </div>

      {/* Model status cards */}
      <div>
        <h3 className="text-lg font-semibold mb-4">AI 모델 상태</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {visibleModels.map(([key, model]) => (
            <ModelCard key={key} name={key} model={model} />
          ))}
        </div>
      </div>

      {/* Admin notice */}
      {role === "admin" && (
        <div className="card border-brand-500/20 bg-brand-600/5">
          <div className="flex items-center gap-3">
            <Cpu size={18} className="text-brand-500" />
            <div>
              <p className="text-sm font-medium text-brand-400">관리자 모드</p>
              <p className="text-xs text-gray-500">
                AIOps 모델 (Model 3) 상태가 표시됩니다. 일반 사용자에게는 보이지 않습니다.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ModelCard({ name, model }: { name: string; model: ModelStatus }) {
  const info = MODEL_INFO[name];
  const style = STATUS_STYLES[model.status];
  if (!info || !style) return null;
  const Icon = info.icon;

  return (
    <div className={`card border ${style.bg} transition-all duration-300`}>
      <div className="flex items-start justify-between mb-4">
        <div className="w-10 h-10 bg-surface-tertiary rounded-xl flex items-center justify-center">
          <Icon size={18} className={style.text} />
        </div>
        <div className="flex items-center gap-2">
          <div className={`status-dot ${style.dot}`} />
          <span className={`text-xs font-mono font-medium ${style.text}`}>
            {style.label}
          </span>
        </div>
      </div>
      <h4 className="font-semibold text-sm">{info.label}</h4>
      <p className="text-xs text-gray-500 mt-1">{info.desc}</p>
      {model.admin_only && (
        <span className="inline-block mt-3 text-[10px] font-mono bg-brand-600/15 text-brand-400 px-2 py-0.5 rounded-md">
          ADMIN ONLY
        </span>
      )}
    </div>
  );
}
