import type { Sample } from '../../types/dashboard';
export function Trend({samples, metric, seconds}: {samples: Sample[]; metric: string; seconds: number}) {
  const end = samples.at(-1)?.time ?? 0;
  const points = samples.filter(s => s.time >= end-seconds);
  let previous: Sample | null = null;
  const paths: string[] = [];
  for (const s of points) {
    const value = s.values[metric];
    if (typeof value !== 'number') {previous = null; continue;}
    const x = 10+(s.time-end+seconds)/seconds*480, y = 90-value*80;
    paths.push(`${previous && s.time-previous.time <= 15 ? 'L' : 'M'}${x},${y}`);
    previous = s;
  }
  return <figure className="trend"><svg viewBox="0 0 500 110" role="img" aria-label={`${metric} timestamped Cortex trend, ${seconds} seconds, gaps indicate unavailable measurements`}><path d="M10 10 V90 H490" stroke="#a6a9b3" fill="none"/><path d={paths.join(' ')} stroke="#72df87" fill="none" strokeWidth="2"/><text x="10" y="107">{end ? new Date((end-seconds)*1000).toLocaleTimeString() : 'Waiting'}</text><text x="490" y="107" textAnchor="end">{end ? new Date(end*1000).toLocaleTimeString() : ''}</text></svg></figure>;
}
