import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  elevated?: boolean;
}

export default function Card({ children, className = '', elevated = false }: CardProps) {
  return (
    <div
      className={[
        'rounded-[var(--radius-lg)] border',
        elevated
          ? 'border-[var(--border-hairline-strong)] bg-[var(--surface-1)]'
          : 'border-[var(--border-default)] bg-[var(--surface-1)]',
        className,
      ].join(' ')}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title?: string;
  children?: React.ReactNode;
  subtitle?: string;
  icon?: React.ReactNode;
  badge?: string;
  badgeVariant?: 'default' | 'online' | 'offline' | 'warning' | 'error' | 'info' | 'idle';
  action?: React.ReactNode;
}

export function CardHeader({
  title,
  subtitle,
  icon,
  badge,
  badgeVariant,
  action,
  children,
}: CardHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-3 px-5 py-4">
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-[var(--accent)]">{icon}</span>}
        {children || (
          <div>
            <h2 className="text-[15px] font-medium leading-none text-[var(--text-ink)]">
              {title}
            </h2>
            {subtitle && (
              <p className="mt-1 text-[12px] text-[var(--text-subtle)]">{subtitle}</p>
            )}
          </div>
        )}
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        {badge && (
          <span
            className={[
              'inline-flex items-center gap-1.5 rounded-[var(--radius-pill)]',
              'px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide',
              badgeVariant === 'online' && 'bg-[var(--success-soft)] text-[var(--success)]',
              badgeVariant === 'offline' && 'bg-[var(--error-soft)] text-[var(--error)]',
              badgeVariant === 'warning' && 'bg-[var(--warning-soft)] text-[var(--warning)]',
              badgeVariant === 'error' && 'bg-[var(--error-soft)] text-[var(--error)]',
              badgeVariant === 'info' && 'bg-[var(--accent-soft)] text-[var(--accent)]',
              badgeVariant === 'idle' && 'bg-[var(--surface-2)] text-[var(--text-subtle)]',
              (!badgeVariant || badgeVariant === 'default') && 'bg-[var(--surface-2)] text-[var(--text-muted)]',
            ].join(' ')}
          >
            <span className="relative flex h-1.5 w-1.5">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-current opacity-75" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
            </span>
            {badge}
          </span>
        )}
        {action && <div>{action}</div>}
      </div>
    </div>
  );
}

interface CardBodyProps {
  children: React.ReactNode;
  className?: string;
}

export function CardBody({ children, className = '' }: CardBodyProps) {
  return <div className={[className, 'px-5 pb-5'].join(' ')}>{children}</div>;
}