'use client';

import { cn } from '@/lib/utils';

interface ScoreBarProps {
  value: number;
  max?: number;
  className?: string;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function ScoreBar({
  value,
  max = 100,
  className,
  showValue = true,
  size = 'md',
}: ScoreBarProps) {
  const percentage = Math.min((value / max) * 100, 100);

  const getColorClass = (pct: number) => {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 60) return 'bg-yellow-500';
    if (pct >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className={cn('flex-1 rounded-full bg-muted', sizeClasses[size])}>
        <div
          className={cn('rounded-full transition-all', sizeClasses[size], getColorClass(percentage))}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showValue && (
        <span className="text-xs font-medium text-muted-foreground w-8 text-right">
          {Math.round(value)}
        </span>
      )}
    </div>
  );
}
