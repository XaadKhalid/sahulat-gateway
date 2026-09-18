'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  Inbox,
  LayoutDashboard,
  Menu,
  MessageCircle,
  MessagesSquare,
  Route as RouteIcon,
  ScrollText,
  Shield,
  UserRound,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/tenants', label: 'Tenants', icon: RouteIcon },
  { to: '/users', label: 'Users', icon: UserRound },
  { to: '/policy', label: 'Policy', icon: Shield },
  { to: '/inbox', label: 'Inbox', icon: Inbox },
  { to: '/conversations', label: 'Conversations', icon: MessagesSquare },
  { to: '/audit', label: 'Audit', icon: ScrollText },
  { to: '/analytics', label: 'Analytics', icon: Activity },
  { to: '/onboarding', label: 'Onboarding', icon: RouteIcon },
] as const;

export function ConsoleShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const items = NAV.map((item) => {
    const active =
      item.to === '/'
        ? pathname === '/' || pathname === ''
        : pathname === item.to || pathname.startsWith(`${item.to}/`);
    return (
      <Link
        key={item.to}
        href={item.to}
        onClick={() => setOpen(false)}
        className={cn(
          'flex min-h-11 items-center gap-3 rounded-md px-3 text-sm transition-colors duration-150',
          active
            ? 'bg-green-soft text-green-deep'
            : 'text-ink-2 hover:bg-muted hover:text-ink',
        )}
      >
        <item.icon className="size-4 shrink-0" />
        {item.label}
      </Link>
    );
  });

  return (
    <div className="min-h-svh bg-paper">
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-paper/95 px-4 backdrop-blur md:hidden">
        <Link href="/" className="font-display text-lg text-ink">
          Sahulat
        </Link>
        <Button
          variant="ghost"
          size="icon"
          aria-label={open ? 'Close menu' : 'Open menu'}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X /> : <Menu />}
        </Button>
      </header>
      {open ? (
        <div className="fixed inset-x-0 top-14 z-20 border-b border-line bg-card p-3 md:hidden">
          <nav className="flex flex-col gap-1">{items}</nav>
        </div>
      ) : null}

      <div className="mx-auto grid max-w-7xl md:grid-cols-[220px_1fr]">
        <aside className="sticky top-0 hidden h-svh border-r border-line p-5 md:flex md:flex-col">
          <Link href="/" className="mb-1 font-display text-xl text-ink">
            Sahulat
          </Link>
          <p className="mb-6 text-xs leading-snug text-mute">
            Control plane
          </p>
          <nav className="flex flex-col gap-1 overflow-auto">{items}</nav>
        </aside>
        <main className="min-w-0 px-4 py-6 md:px-8 md:py-8">{children}</main>
      </div>
    </div>
  );
}
