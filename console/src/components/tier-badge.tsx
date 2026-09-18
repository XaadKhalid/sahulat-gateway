import { Badge } from '@/components/ui/badge';

export type IdentityTier = 'anonymous' | 'known' | 'verified' | 'privileged';

const MAP: Record<
  IdentityTier,
  { label: string; variant: 'mute' | 'slate' | 'default' | 'amber' }
> = {
  anonymous: { label: 'Anonymous', variant: 'mute' },
  known: { label: 'Known', variant: 'slate' },
  verified: { label: 'Verified', variant: 'default' },
  privileged: { label: 'Privileged', variant: 'amber' },
};

export function TierBadge({ tier }: { tier: IdentityTier }) {
  const m = MAP[tier];
  return <Badge variant={m.variant}>{m.label}</Badge>;
}
