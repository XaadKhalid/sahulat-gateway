'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuth } from '@/components/providers';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace('/login');
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-gray-950 text-gray-400">
        Loading…
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <nav className="flex w-64 flex-shrink-0 flex-col border-r border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 p-4">
          <h1 className="text-xl font-bold">Sahulat Gateway</h1>
          <p className="mt-1 text-xs text-gray-500">{user.email}</p>
          <span className="text-xs text-gray-600">Role: {user.role}</span>
        </div>
        <ul className="flex-1 space-y-1 p-2">
          <li>
            <Link
              href="/tenants"
              className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100"
            >
              Tenants
            </Link>
          </li>
          <li>
            <Link
              href="/users"
              className="block rounded-md px-3 py-2 text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100"
            >
              Users
            </Link>
          </li>
        </ul>
        <div className="border-t border-gray-800 p-4">
          <button
            onClick={logout}
            className="w-full rounded-md px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-800 hover:text-gray-100"
          >
            Sign out
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  );
}
