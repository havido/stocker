import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { apiPost, setToken, clearToken, TOKEN_KEY } from "@/lib/api";

interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<{ needsConfirmation: boolean }>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  login: async () => {},
  register: async () => ({ needsConfirmation: false }),
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      // We have a stored token — trust it for now.
      // The API client will redirect on 401 if it's expired.
      const storedUser = localStorage.getItem("stocker_user");
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setTokenState(stored);
        } catch {
          clearToken();
          localStorage.removeItem("stocker_user");
        }
      }
    }
    setIsLoading(false);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost("/v1/auth/login", { email, password });
    const u: User = { id: data.user_id, email: data.email };
    setToken(data.access_token);
    localStorage.setItem("stocker_user", JSON.stringify(u));
    setTokenState(data.access_token);
    setUser(u);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    const data = await apiPost("/v1/auth/register", { email, password });
    if (!data.access_token) {
      // Email confirmation required
      return { needsConfirmation: true };
    }
    const u: User = { id: data.user_id, email: data.email };
    setToken(data.access_token);
    localStorage.setItem("stocker_user", JSON.stringify(u));
    setTokenState(data.access_token);
    setUser(u);
    return { needsConfirmation: false };
  }, []);

  const logout = useCallback(() => {
    clearToken();
    localStorage.removeItem("stocker_user");
    setTokenState(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
