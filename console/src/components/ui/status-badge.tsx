import { Badge } from '@/components/ui/badge';
import { cva, type VariantProps } from 'class-variance-authority';

const statusVariants = cva('', {
  variants: {
    status: {
      live: 'border-transparent bg-green-soft text-green-deep',
      connecting: 'border-transparent bg-amber-soft text-amber',
      suspended: 'border-transparent bg-danger-soft text-danger',
      draft: 'border-transparent bg-muted text-mute',
    },
  },
  defaultVariants: { status: 'draft' },
});

export function StatusBadge({ status }: { status: 'draft' | 'connecting' | 'live' | 'suspended' }) {
  return (
    <Badge variant="default" className={statusVariants({ status })}>
      {status}
    </Badge>
  );
}
