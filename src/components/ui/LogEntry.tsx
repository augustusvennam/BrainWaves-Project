import React from 'react';

type LogEntryLevel = 'info' | 'warn' | 'error';

interface LogEntryProps {
  id: string | number;
  time: string;
  level: LogEntryLevel;
  message: string;
}

const levelStyles: Record<LogEntryLevel, string> = {
  info: 'text-[var(--accent)]',
  warn: 'text-[var(--warning)]',
  error: 'text-[var(--error)]',
};

const levelIcon: Record<LogEntryLevel, string> = {
  info: 'i',
  warn: '!',
  error: 'x',
};

function formatTime(isoString: string): string {
  let date: Date;
  if (isoString.includes('T')) {
    date = new Date(isoString);
  } else {
    date = new Date(isoString.replace(' ', 'T'));
  }
  if (isNaN(date.getTime())) return isoString;
  return date.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

export default function LogEntry({ id, time, level, message }: LogEntryProps) {
  return (
    <div
      key={id}
      className="group flex gap-3 px-4 py-2 transition-colors duration-[var(--duration-fast)] hover:bg-[var(--surface-2)]"
    >
      <time
        className="mono text-[11px] leading-6 text-[var(--text-tertiary)] tabular-nums flex-shrink-0 pt-1"
        dateTime={time}
      >
        {formatTime(time)}
      </time>
      <span
        className={[
          'flex h-5 w-5 items-center justify-center rounded-[var(--radius-xs)]',
          'text-[10px] font-bold flex-shrink-0 mt-0.5',
          level === 'info' && 'bg-[var(--accent-soft)] text-[var(--accent)]',
          level === 'warn' && 'bg-[var(--warning-soft)] text-[var(--warning)]',
          level === 'error' && 'bg-[var(--error-soft)] text-[var(--error)]',
        ].join(' ')}
        aria-label={level}
      >
        {levelIcon[level]}
      </span>
      <p className={['text-[13px] leading-6 flex-1 min-w-0', levelStyles[level]].join(' ')}>
        {message}
      </p>
    </div>
  );
}