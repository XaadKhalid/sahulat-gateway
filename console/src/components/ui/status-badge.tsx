interface StatusBadgeProps {
  status: 'draft' | 'connecting' | 'live' | 'suspended';
}

const STATUS_STYLES: Record<StatusBadgeProps['status'], string> = {
  live: 'bg-green-900/30 text-green-400',
  connecting: 'bg-yellow-900/30 text-yellow-400',
  suspended: 'bg-red-900/30 text-red-400',
  draft: 'bg-gray-800 text-gray-400',
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${STATUS_STYLES[status]}`}>
      {status}
    </span>
  );
}
