import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

import { api, clearTokens, getTokens, setTokens } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Restore the session on first load if tokens exist.
  useEffect(() => {
    const { access, refresh } = getTokens();
    if (!access && !refresh) {
      setLoading(false);
      return;
    }
    api("/api/auth/me")
      .then(setUser)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    setTokens(data);
    setUser(data.user);
  }, []);

  const register = useCallback(async (fullName, email, password) => {
    const data = await api("/api/auth/register", {
      method: "POST",
      body: { full_name: fullName, email, password },
      auth: false,
    });
    setTokens(data);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    const { refresh } = getTokens();
    if (refresh) {
      try {
        await api("/api/auth/logout", {
          method: "POST",
          body: { refresh_token: refresh },
          auth: false,
        });
      } catch {
        // Best effort - clear locally regardless.
      }
    }
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
