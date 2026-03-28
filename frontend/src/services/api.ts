/**
 * Gateway API 클라이언트
 * 모든 백엔드 통신을 이 파일에서 관리.
 */

const API_BASE = "/api";

function getHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Auth ──

export async function login(username: string, password: string) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error("로그인 실패");
  const data = await res.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("role");
}

export function isLoggedIn(): boolean {
  return !!localStorage.getItem("token");
}

// ── Health Check ──

export interface ModelStatus {
  status: "green" | "orange" | "red";
  admin_only: boolean;
}

export interface HealthData {
  gateway: string;
  models: Record<string, ModelStatus>;
}

export async function fetchHealth(): Promise<HealthData> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error("헬스체크 실패");
  return res.json();
}

// ── Phishing Check ──

export interface PhishingResult {
  url: string;
  is_phishing: boolean;
  confidence: number;
  risk_level: "safe" | "warning" | "danger";
  details: Record<string, unknown> | null;
}

export async function checkUrl(url: string): Promise<PhishingResult> {
  const res = await fetch(`${API_BASE}/phishing/check`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error("검사 실패");
  return res.json();
}

// ── Sandbox ──

export interface SandboxResult {
  sandbox_id: string;
  novnc_url: string;
  target_url: string;
  status: string;
}

export async function assignSandbox(url: string): Promise<SandboxResult> {
  const res = await fetch(`${API_BASE}/sandbox/assign`, {
    method: "POST",
    headers: getHeaders(),
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error("샌드박스 할당 실패");
  return res.json();
}

export async function releaseSandbox(containerId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sandbox/release/${containerId}`, {
    method: "POST",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("샌드박스 반환 실패");
}

// ── Admin: Pool 관리 ──

export interface ContainerInfo {
  container_id: string;
  status: string;
  novnc_port: number;
  novnc_url: string;
  assigned_to: string | null;
  target_url: string | null;
  cpu_limit: string;
  memory_limit: string;
}

export interface PoolStatus {
  pool_size: number;
  total: number;
  idle: number;
  assigned: number;
  containers: ContainerInfo[];
}

export async function fetchPoolStatus(): Promise<PoolStatus> {
  const res = await fetch(`${API_BASE}/sandbox/pool`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("Pool 상태 조회 실패");
  return res.json();
}

export async function updatePoolConfig(config: {
  pool_size?: number;
  default_cpu_limit?: string;
  default_memory_limit?: string;
}): Promise<void> {
  const res = await fetch(`${API_BASE}/sandbox/pool/config`, {
    method: "PUT",
    headers: getHeaders(),
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error("Pool 설정 변경 실패");
}

export async function forceRemoveContainer(containerId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/sandbox/container/${containerId}`, {
    method: "DELETE",
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("컨테이너 삭제 실패");
}

// ── Admin: 서버 리소스 ──

export interface ServerResources {
  cpu_percent: number;
  memory_percent: number;
  memory_total_gb: number;
  memory_used_gb: number;
  disk_percent: number;
  disk_total_gb: number;
  disk_used_gb: number;
}

export async function fetchServerResources(): Promise<ServerResources> {
  const res = await fetch(`${API_BASE}/sandbox/resources`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error("리소스 조회 실패");
  return res.json();
}
