import React from 'react';
import { CheckCircle2, Circle, Clock } from 'lucide-react';

type MilestoneStatus = 'complete' | 'in-progress' | 'pending';

interface MilestoneProps {
  id: string;
  title: string;
  description: string;
  status: MilestoneStatus;
  onClick?: () => void;
}

const statusConfig: Record<MilestoneStatus, {
  badge: string;
  variant: 'online' | 'warning' | 'info' | 'idle';
  icon: React.ElementType;
  iconColor: string;
}> = {
  complete: {
    badge: 'Complete',
    variant: 'online',
    icon: CheckCircle2,
    iconColor: 'text-[var(--success)]',
  },
  'in-progress': {
    badge: 'In Progress',
    variant: 'warning',
    icon: Clock,
    iconColor: 'text-[var(--warning)]',
  },
  pending: {
    badge: 'Pending',
    variant: 'info',
    icon: Circle,
    iconColor: 'text-[var(--accent)]',
  },
};

export default function MilestoneCard({
  id,
  title,
  description,
  status,
  onClick,
}: MilestoneProps) {
  const { badge, variant, icon: Icon } = statusConfig[status];

  return (
    <button
      type="button"
      onClick={onClick}
      data-milestone-id={id}
      className={[
        'group relative flex items-start gap-3 rounded-[var(--radius-lg)]',
        'border border-[var(--border-default)] bg-[var(--surface-1)]',
        'p-4 text-left transition-all duration-[var(--duration-normal)] ease-[var(--easing-out)]',
        'hover:border-[var(--border-hairline-strong)] hover:bg-[var(--surface-2)]',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--surface-canvas)]',
        onClick ? 'cursor-pointer' : 'cursor-default',
      ].join(' ')}
      aria-label={`${title}: ${badge}`}
    >
      <span className={`flex-shrink-0 mt-0.5 ${statusConfig[status].iconColor}`}>
        <Icon size={16} strokeWidth={2} />
      </span>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-[13px] font-medium leading-none text-[var(--text-ink)] truncate">
            {title}
          </h3>
          <span
            className={[
              'flex-shrink-0 rounded-[var(--radius-pill)]',
              'px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
              variant === 'online' && 'bg-[var(--success-soft)] text-[var(--success)]',
              variant === 'warning' && 'bg-[var(--warning-soft)] text-[var(--warning)]',
              variant === 'info' && 'bg-[var(--accent-soft)] text-[var(--accent)]',
              variant === 'idle' && 'bg-[var(--surface-2)] text-[var(--text-subtle)]',
            ].join(' ')}
          >
            {badge}
          </span>
        </div>
        <p className="mt-1.5 text-[12px] leading-relaxed text-[var(--text-subtle)] line-clamp-2">
          {description}
        </p>
      </div>
    </button>
  );
}