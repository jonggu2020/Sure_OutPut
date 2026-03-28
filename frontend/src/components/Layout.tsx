import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Shield, Search, Monitor, LogOut, Activity, Settings } from "lucide-react";

const navItems = [
  { to: "/", icon: Activity, label: "대시보드", adminOnly: false },
  { to: "/scan", icon: Search, label: "URL 검사", adminOnly: false },
  { to: "/sandbox", icon: Monitor, label: "샌드박스", adminOnly: false },
  { to: "/admin", icon: Settings, label: "관리자", adminOnly: true },
];

export default function Layout() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-surface-secondary border-r border-gray-800/50 flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center">
              <Shield size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">SecureOps</h1>
              <span className="text-xs text-gray-500 font-mono">
                {role === "admin" ? "ADMIN" : "USER"}
              </span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1">
          {navItems
            .filter((item) => !item.adminOnly || role === "admin")
            .map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-brand-600/15 text-brand-500 border border-brand-500/20"
                      : "text-gray-400 hover:text-white hover:bg-surface-tertiary"
                  }`
                }
              >
                <Icon size={18} />
                {label}
              </NavLink>
            ))}
        </nav>

        {/* Logout */}
        <div className="p-4 border-t border-gray-800/50">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-gray-400
                       hover:text-red-400 hover:bg-red-500/10 transition-all duration-200 w-full"
          >
            <LogOut size={18} />
            로그아웃
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
    </div>
  );
}
