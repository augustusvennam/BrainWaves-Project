import type { Snapshot } from '../../types/dashboard';
export function streamMessage(snapshot: Snapshot | null, name: string) {
  if (!snapshot) return 'Waiting for backend.';
  if (snapshot.rejected_streams[name]) return `Unavailable: ${snapshot.rejected_streams[name]}`;
  const stream = snapshot.streams[name];
  if (!stream) return 'Not subscribed. Check CORTEX_STREAMS and license access.';
  if (stream.age_seconds === null) return 'Subscribed; waiting for data.';
  return `Last sample ${stream.age_seconds.toFixed(1)} s ago${stream.observed_hz === null ? '' : ` · observed ${stream.observed_hz} Hz`}`;
}
export function StreamPanel({ snapshot }: { snapshot: Snapshot | null }) {
  return <section className="panel"><h2>Stream availability</h2>
    <div className="stream-list">{['eeg', 'pow', 'met', 'com', 'dev', 'eq', 'sys'].map(name =>
      <div key={name}><code>{name}</code><span>{streamMessage(snapshot, name)}</span></div>)}</div>
    <p className="hint">Rates are measured from received samples, not assumed from configuration. System events arrive only when events occur.</p>
  </section>;
}
