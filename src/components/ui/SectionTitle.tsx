interface SectionTitleProps {
  children: React.ReactNode;
  className?: string;
}

export function SectionTitle({ children, className = '' }: SectionTitleProps) {
  return (
    <h2 className={[
      'text-[15px] font-medium leading-none text-[var(--text-ink)]',
      'letter-spacing:-0.02em',
      className,
    ].join(' ')}>{children}</h2>
  );
}