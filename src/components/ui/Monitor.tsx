import React from 'react';
import { Badge } from './Badge';

type MonitorStatus = 'online' | 'offline' | 'idle' | 'connecting';

interface MonitorProps {
  id: string;
  title: string;
  status: MonitorStatus;
  detail: string;
  icon: React.ReactNode;
}

const statusMap: Record<MonitorStatus, { label: string; variant: 'online' | 'offline' | 'idle' | 'warning' }> = {
  online: { label: 'Online', variant: 'online' },
  offline: { label: 'Offline', variant: 'offline' },
  idle: { label: 'Idle', variant: 'idle' },
  connecting: { label: 'Connecting', variant: 'warning' },
};

export default function Monitor({ id, title, status, detail, icon }: MonitorProps) {
  const { label, variant } = statusMap[status];

  return (
    <div
      className="group relative rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--surface-1)] p-4 transition-colors duration-[var(--duration-normal)] ease-[var(--easing-out)] hover:border-[var(--border-hairline-strong)]"
      role="status"
      aria-label={`${title}: ${label}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--surface-2)] text-[var(--accent)]">
            {icon}
          </div>
          <div>
            <h3 className="text-[13px] font-medium leading-none text-[var(--text-ink)]">
              {title}
            </h3>
          </div>
        </div>
        <Badge label={label} variant={variant} dot />
      </div>
      <div className="mt-3">
        <p className="text-[12px] leading-relaxed text-[var(--text-subtle)]">
          {detail}
        </p>
      </div>
      <div className="absolute inset-x-4 bottom-0 h-px bg-[var(--border-hairline)]" />
    </div>
  );
}