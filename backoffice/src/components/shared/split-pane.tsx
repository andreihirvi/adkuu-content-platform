'use client';

import { cn } from '@/lib/utils';

interface SplitPaneProps {
  left: React.ReactNode;
  right: React.ReactNode;
  leftWidth?: string;
  className?: string;
}

export function SplitPane({
  left,
  right,
  leftWidth = '400px',
  className,
}: SplitPaneProps) {
  return (
    <div className={cn('flex h-[calc(100vh-8rem)] gap-4', className)}>
      <div
        className="shrink-0 overflow-hidden rounded-lg border bg-card"
        style={{ width: leftWidth }}
      >
        {left}
      </div>
      <div className="flex-1 overflow-hidden rounded-lg border bg-card">
        {right}
      </div>
    </div>
  );
}
