interface BadgeProps {
  label: string;
  variant?: 'default' | 'online' | 'offline' | 'warning' | 'error' | 'info' | 'idle';
  dot?: boolean;
  className?: string;
}

const variantStyles: Record<string, string> = {
  default: 'bg-[var(--surface-2)] text-[var(--text-muted)]',
  online: 'bg-[var(--success-soft)] text-[var(--success)]',
  offline: 'bg-[var(--error-soft)] text-[var(--error)]',
  warning: 'bg-[var(--warning-soft)] text-[var(--warning)]',
  error: 'bg-[var(--error-soft)] text-[var(--error)]',
  info: 'bg-[var(--accent-soft)] text-[var(--accent)]',
  idle: 'bg-[var(--surface-2)] text-[var(--text-subtle)]',
};

export default function Badge({
  label,
  variant = 'default',
  dot = true,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-(--radius-pill)',
        'px-2 py-0.5 text-[11px] font-medium',
        'transition-colors duration-(--duration-fast)',
        variantStyles[variant],
        className,
      ].join(' ')}
    >
      {dot && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-current" />
        </span>
      )}
      {label}
    </span>
  );
}