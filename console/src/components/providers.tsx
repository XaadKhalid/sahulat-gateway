'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { client } from '@/lib/api-client/client';

type MeResponse = { id: string; email: string; role: 'admin' | 'operator' };

interface AuthContextValue {
  user: MeResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    client.GET('/auth/me').then(({ data }) => {
      if (active) {
        setUser(data ?? null);
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  async function login(email: string, password: string): Promise<boolean> {
    const { data } = await client.POST('/auth/login', {
      body: { email, password },
    });
    if (data) {
      setUser(data);
      return true;
    }
    return false;
  }

  async function logout() {
    await client.POST('/auth/logout');
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function RootProviders({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    async function boot() {
      if (process.env.NODE_ENV === 'development') {
        const { worker } = await import('@/lib/mocks/browser');
        await worker.start();
      }
      setReady(true);
    }
    boot();
  }, []);

  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-950 text-gray-400">
        Initializing…
      </div>
    );
  }

  return <AuthProvider>{children}</AuthProvider>;
}
