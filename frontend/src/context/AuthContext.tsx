import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Skeleton } from "../components/ui";
import {
  ensureCsrfToken,
  extractApiErrorMessage,
  type AuthUser,
  type LoginPayload,
  type RegisterPayload,
} from "../types/auth";
import type { AudienceTier } from "../types/catalog";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  login: (payload: LoginPayload) => Promise<AuthUser>;
  register: (payload: RegisterPayload) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<AuthUser | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export interface AuthProviderProps {
  children: ReactNode;
  onAudienceSync?: (audience: AudienceTier) => void;
}

export function AuthProvider({ children, onAudienceSync }: AuthProviderProps) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const syncUserAudience = useCallback(
    (nextUser: AuthUser | null) => {
      const serverAudience = nextUser?.profile?.effective_audience;
      if (serverAudience && onAudienceSync) {
        onAudienceSync(serverAudience);
      }
    },
    [onAudienceSync]
  );

  const refreshUser = useCallback(async (): Promise<AuthUser | null> => {
    try {
      await ensureCsrfToken();
      const response = await fetch("/api/auth/me/", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
      });

      if (!response.ok) {
        setUser(null);
        return null;
      }

      const currentUser = (await response.json()) as AuthUser;
      setUser(currentUser);
      syncUserAudience(currentUser);
      return currentUser;
    } catch {
      setUser(null);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [syncUserAudience]);

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const login = useCallback(
    async (payload: LoginPayload): Promise<AuthUser> => {
      const csrfToken = await ensureCsrfToken();
      const response = await fetch("/api/auth/login/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      const data: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          extractApiErrorMessage(data, "Invalid email or password.")
        );
      }

      const authenticatedUser = data as AuthUser;
      setUser(authenticatedUser);
      syncUserAudience(authenticatedUser);
      return authenticatedUser;
    },
    [syncUserAudience]
  );

  const register = useCallback(
    async (payload: RegisterPayload): Promise<AuthUser> => {
      const csrfToken = await ensureCsrfToken();
      const response = await fetch("/api/auth/register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          "X-CSRFToken": csrfToken,
        },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      const data: unknown = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(
          extractApiErrorMessage(data, "Unable to complete registration.")
        );
      }

      const createdUser = data as AuthUser;
      setUser(createdUser);
      syncUserAudience(createdUser);
      return createdUser;
    },
    [syncUserAudience]
  );

  const logout = useCallback(async (): Promise<void> => {
    const csrfToken = await ensureCsrfToken();
    await fetch("/api/auth/logout/", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "X-CSRFToken": csrfToken,
      },
      credentials: "same-origin",
    });
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}

/**
 * UX route guard for authenticated student screens.
 * Note: Server-side DRF IsAuthenticated permissions remain the security authority.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-12 space-y-4">
        <Skeleton className="h-8 w-64" label="Checking student session" />
        <Skeleton className="h-44 w-full" label="Loading student portal" />
      </div>
    );
  }

  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <>{children}</>;
}