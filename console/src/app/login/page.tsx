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
    <div className="flex h-screen w-full items-center justify-center bg-paper">
      <form
        onSubmit={handleSubmit}
        className="w-80 space-y-6 rounded-xl border border-line bg-card p-8"
      >
        <div className="text-center">
          <h1 className="font-display text-xl text-ink">Sahulat Gateway</h1>
          <p className="mt-1 text-sm text-mute">Sign in to continue</p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-ink-2">Email</label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-mute focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="admin@acme.com"
            autoComplete="email"
            required
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium text-ink-2">Password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            className="w-full rounded-md border border-line bg-card px-3 py-2 text-sm text-ink placeholder:text-mute focus:outline-none focus:ring-2 focus:ring-ring"
            placeholder="password"
            autoComplete="current-password"
            required
          />
        </div>

        {error && <p className="text-sm text-danger">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-green px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-green-deep disabled:opacity-50"
        >
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
