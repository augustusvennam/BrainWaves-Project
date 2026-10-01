interface SectionSubtitleProps {
  children: React.ReactNode;
  className?: string;
}

export function SectionSubtitle({ children, className = '' }: SectionSubtitleProps) {
  return (
    <p className={[
      'text-[12px] leading-relaxed text-[var(--text-subtle)]',
      className,
    ].join(' ')}>{children}</p>
  );
}