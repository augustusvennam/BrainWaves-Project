import type { Snapshot } from '../../types/dashboard';
import { streamMessage } from './StreamPanel';
const labels: Record<string, string> = { eng: 'Engagement', exc: 'Excitement', lex: 'Long-term excitement', str: 'Stress', rel: 'Relaxation', int: 'Interest', attention: 'Attention' };
export function Metrics({ snapshot }: { snapshot: Snapshot | null }) {
  const values = snapshot?.latest.met?.values ?? {};
  const age = snapshot?.streams.met?.age_seconds;
  return <section className="panel"><h2>Performance metrics</h2><p className="hint">{streamMessage(snapshot, 'met')}</p>
    {age !== null && age !== undefined && age > 15 && <p className="warning">Stale metrics — showing last received values.</p>}
    {Object.keys(values).length ? <div className="metrics">{Object.entries(values).map(([name, value]) =>
      <div key={name}><div className="row"><span>{labels[name] ?? name}</span><strong>{typeof value === 'number' ? value.toFixed(2) : 'Unavailable'}</strong></div>
        {typeof value === 'number' && <meter min={0} max={1} value={value} aria-label={labels[name] ?? name} />}</div>)}</div> : <p className="empty">No performance metrics received.</p>}
    <p className="hint">Cortex estimates, not a diagnosis or validated emotion classifier. Inactive or missing metrics stay unavailable.</p>
  </section>;
}
