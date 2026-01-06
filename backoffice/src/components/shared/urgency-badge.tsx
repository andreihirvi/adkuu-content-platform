'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { UrgencyLevel } from '@/types';

interface UrgencyBadgeProps {
  level: UrgencyLevel;
  className?: string;
}

const urgencyConfig: Record<
  UrgencyLevel,
  { label: string; className: string }
> = {
  critical: {
    label: 'Critical',
    className: 'bg-red-500 text-white hover:bg-red-600',
  },
  high: {
    label: 'High',
    className: 'bg-orange-500 text-white hover:bg-orange-600',
  },
  medium: {
    label: 'Medium',
    className: 'bg-yellow-500 text-white hover:bg-yellow-600',
  },
  low: {
    label: 'Low',
    className: 'bg-green-500 text-white hover:bg-green-600',
  },
};

export function UrgencyBadge({ level, className }: UrgencyBadgeProps) {
  const config = urgencyConfig[level];

  return (
    <Badge className={cn(config.className, className)}>
      {config.label}
    </Badge>
  );
}
