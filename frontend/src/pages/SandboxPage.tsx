import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { releaseSandbox } from "../services/api";
import { Radio, Clock, XCircle, Loader2 } from "lucide-react";

export default function SandboxPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const sandboxId = searchParams.get("id") || "";
  const novncUrl = searchParams.get("novnc") || "";
  const targetUrl = searchParams.get("url") || "";

  const [elapsed, setElapsed] = useState(0);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [releasing, setReleasing] = useState(false);
  const [ready, setReady] = useState(false);

  // 경과 시간 타이머
  useEffect(() => {
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  // 컨테이너 준비 대기 (3초 후 iframe 표시)
  useEffect(() => {
    if (!novncUrl) return;
    const timer = setTimeout(() => setReady(true), 3000);
    return () => clearTimeout(timer);
  }, [novncUrl]);

  // 세션 종료 버튼을 눌렀을 때만 삭제
  async function handleRelease() {
    if (!sandboxId) return;
    setReleasing(true);
    try {
      await releaseSandbox(sandboxId);
    } catch (err) {
      console.error("세션 종료 실패:", err);
    } finally {
      setReleasing(false);
      navigate("/scan");
    }
  }

  function formatTime(seconds: number) {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  }

  const hasValidSandbox = sandboxId && novncUrl;
  const decodedNovncUrl = novncUrl ? decodeURIComponent(novncUrl) : "";

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">샌드박스 모드</h2>
          <p className="text-gray-500 text-sm mt-1 font-mono">
            {targetUrl ? decodeURIComponent(targetUrl) : "대기 중"}
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Radio size={14} className={hasValidSandbox && ready ? "text-green-400" : "text-gray-500"} />
            <span className={`text-xs font-mono ${hasValidSandbox && ready ? "text-green-400" : "text-gray-500"}`}>
              {hasValidSandbox && ready ? "격리 환경 실행 중" : "준비 중..."}
            </span>
          </div>

          <div className="flex items-center gap-2 bg-surface-tertiary rounded-lg px-3 py-1.5">
            <Clock size={14} className="text-gray-500" />
            <span className="text-sm font-mono text-gray-300">{formatTime(elapsed)}</span>
          </div>

          <button
            onClick={handleRelease}
            disabled={releasing || !sandboxId}
            className="btn-danger flex items-center gap-2 text-sm py-2 disabled:opacity-50"
          >
            {releasing ? <Loader2 size={16} className="animate-spin" /> : <XCircle size={16} />}
            세션 종료
          </button>
        </div>
      </div>

      {/* noVNC Viewer */}
      <div className="flex-1 card p-0 overflow-hidden min-h-[500px]">
        {hasValidSandbox ? (
          <div className="relative w-full h-full" style={{ minHeight: "500px" }}>
            {/* 로딩 화면 — ready 전까지 표시 */}
            {(!ready || !iframeLoaded) && (
              <div className="absolute inset-0 flex items-center justify-center bg-surface-tertiary z-10">
                <div className="text-center space-y-4">
                  <Loader2 size={32} className="animate-spin text-brand-500 mx-auto" />
                  <p className="text-gray-400 text-sm">
                    {!ready ? "격리 환경 준비 중..." : "브라우저 연결 중..."}
                  </p>
                  <div className="flex items-center justify-center gap-1">
                    <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}

            {/* noVNC iframe — ready가 된 후에만 로드 */}
            {ready && (
              <iframe
                src={decodedNovncUrl}
                className="w-full h-full border-0"
                title="Sandbox Browser"
                onLoad={() => setIframeLoaded(true)}
                style={{ minHeight: "500px" }}
              />
            )}
          </div>
        ) : (
          <div className="h-full flex items-center justify-center bg-surface-tertiary" style={{ minHeight: "500px" }}>
            <div className="text-center space-y-4">
              <p className="text-gray-400 font-medium">샌드박스가 할당되지 않았습니다</p>
              <p className="text-xs text-gray-600 mt-1">URL 검사 페이지에서 샌드박스 모드를 선택해주세요.</p>
              <button onClick={() => navigate("/scan")} className="btn-primary text-sm">
                URL 검사로 이동
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}