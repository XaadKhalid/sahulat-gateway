'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/providers';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('admin@acme.com');
  const [password, setPassword] = useState('password');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const ok = await login(email, password);
    if (ok) {
      router.replace('/tenants');
    } else {
      setError('Invalid email or password.');
    }
    setSubmitting(false);
  }

  return (
    <div className="flex h-screen w-full items-center justify-center bg-gray-950">
      <form
        onSubmit={handleSubmit}
        className="w-80 space-y-6 rounded-lg border border-gray-800 bg-gray-900 p-8"
      >
        <h1 className="text-center text-xl font-bold text-gray-100">Sahulat Gateway</h1>
        <p className="text-center text-sm text-gray-500">Sign in to continue</p>

        <div className="space-y-2">
          <label className="block text-sm text-gray-300">Email</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            placeholder="admin@acme.com"
            autoComplete="email"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm text-gray-300">Password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-gray-100 placeholder-gray-600 focus:border-blue-500 focus:outline-none"
            placeholder="password"
            autoComplete="current-password"
            required
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
