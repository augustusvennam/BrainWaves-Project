import React from 'react';
import { Info, AlertTriangle, AlertCircle } from 'lucide-react';

type LogEntryLevel = 'info' | 'warn' | 'error';

interface LogEntryProps {
  id: string | number;
  time: string;
  level: LogEntryLevel;
  message: string;
}

const levelIcon: Record<LogEntryLevel, React.ElementType> = {
  info: Info,
  warn: AlertTriangle,
  error: AlertCircle,
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
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export default function LogEntry({ id, time, level, message }: LogEntryProps) {
  const Icon = levelIcon[level];
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
      <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center text-[var(--text-tertiary)] mt-0.5">
        <Icon size={14} strokeWidth={1.5} />
      </span>
      <p className="text-[13px] leading-6 flex-1 min-w-0 text-[var(--text-muted)]">
        {message}
      </p>
    </div>
  );
}