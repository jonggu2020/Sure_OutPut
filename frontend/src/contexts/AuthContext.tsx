import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { isLoggedIn, logout as apiLogout } from "../services/api";

interface AuthCtx {
  authenticated: boolean;
  role: string;
  setAuth: (token: string, role: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>({
  authenticated: false,
  role: "user",
  setAuth: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(isLoggedIn());
  const [role, setRole] = useState(localStorage.getItem("role") || "user");

  function setAuth(token: string, role: string) {
    localStorage.setItem("token", token);
    localStorage.setItem("role", role);
    setAuthenticated(true);
    setRole(role);
  }

  function logout() {
    apiLogout();
    setAuthenticated(false);
    setRole("user");
  }

  return (
    <AuthContext.Provider value={{ authenticated, role, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
