import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { checkUrl, assignSandbox, type PhishingResult } from "../services/api";
import { Search, ShieldCheck, ShieldAlert, ShieldX, Loader2, ExternalLink, Monitor } from "lucide-react";

const RISK_CONFIG = {
  safe: {
    icon: ShieldCheck,
    color: "text-green-400",
    bg: "bg-green-500/10 border-green-500/20",
    label: "안전",
    desc: "위협이 감지되지 않았습니다.",
  },
  warning: {
    icon: ShieldAlert,
    color: "text-amber-400",
    bg: "bg-amber-500/10 border-amber-500/20",
    label: "주의",
    desc: "피싱 의심 요소가 발견되었습니다.",
  },
  danger: {
    icon: ShieldX,
    color: "text-red-400",
    bg: "bg-red-500/10 border-red-500/20",
    label: "위험",
    desc: "높은 확률로 피싱 사이트입니다.",
  },
};

export default function ScanPage() {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [sandboxLoading, setSandboxLoading] = useState(false);
  const [result, setResult] = useState<PhishingResult | null>(null);
  const navigate = useNavigate();

  async function handleScan(e: React.FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const data = await checkUrl(url);
      setResult(data);
    } catch (err) {
      console.error("검사 실패:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSandbox() {
    if (!url) return;
    setSandboxLoading(true);
    try {
      const sandbox = await assignSandbox(url);
      navigate(`/sandbox?id=${sandbox.sandbox_id}&novnc=${encodeURIComponent(sandbox.novnc_url)}&url=${encodeURIComponent(url)}`);
    } catch (err) {
      console.error("샌드박스 할당 실패:", err);
      alert("사용 가능한 샌드박스가 없습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setSandboxLoading(false);
    }
  }

  const risk = result ? RISK_CONFIG[result.risk_level] : null;
  const RiskIcon = risk?.icon;

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">URL 검사</h2>
        <p className="text-gray-500 text-sm mt-1">URL을 입력하면 AI가 피싱 여부를 분석합니다</p>
      </div>

      <form onSubmit={handleScan} className="relative">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" />
            <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} className="input-field w-full pl-12 font-mono text-sm" placeholder="https://example.com" required />
          </div>
          <button type="submit" disabled={loading} className="btn-primary flex items-center gap-2 disabled:opacity-50">
            {loading ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
            검사
          </button>
        </div>
      </form>

      {result && risk && RiskIcon && (
        <div className={`card border ${risk.bg} space-y-6`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <RiskIcon size={28} className={risk.color} />
              <div>
                <h3 className={`text-xl font-bold ${risk.color}`}>{risk.label}</h3>
                <p className="text-sm text-gray-400">{risk.desc}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">신뢰도</p>
              <p className={`text-2xl font-bold font-mono ${risk.color}`}>{(result.confidence * 100).toFixed(1)}%</p>
            </div>
          </div>

          <div className="bg-surface-tertiary rounded-xl px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">검사 URL</p>
            <p className="font-mono text-sm text-gray-300 break-all">{result.url}</p>
          </div>

          {result.details && (
            <div>
              <p className="text-xs text-gray-500 mb-3">탐지 상세</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(result.details).map(([key, val]) => (
                  <div key={key} className="bg-surface-tertiary rounded-lg px-3 py-2">
                    <p className="text-[10px] text-gray-500 font-mono">{key}</p>
                    <p className="text-sm font-medium font-mono mt-0.5">{typeof val === "object" ? JSON.stringify(val) : String(val)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 샌드박스 버튼 — 결과에 상관없이 항상 표시 */}
          <div className="flex gap-3 pt-2 border-t border-gray-800/50">
            {result.risk_level !== "safe" && (
              <button onClick={() => window.open(url, "_blank")} className="btn-warning flex items-center gap-2 text-sm">
                <ExternalLink size={16} />
                강제 접속
              </button>
            )}
            <button onClick={handleSandbox} disabled={sandboxLoading} className="btn-primary flex items-center gap-2 text-sm disabled:opacity-50">
              {sandboxLoading ? <Loader2 size={16} className="animate-spin" /> : <Monitor size={16} />}
              샌드박스 모드
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
