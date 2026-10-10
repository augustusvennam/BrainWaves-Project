import { Electrodes } from './Electrodes';
import type { Snapshot } from '../../types/dashboard';
import { streamMessage } from './StreamPanel';
export function Quality({ snapshot }: { snapshot: Snapshot | null }) {
  return <section className="panel"><h2>Headset & signal quality</h2><Electrodes snapshot={snapshot} />
    {(['dev', 'eq'] as const).map(stream => <div key={stream}><h3>{stream === 'dev' ? 'Contact quality / device' : 'EEG quality'}</h3><p className="hint">{streamMessage(snapshot, stream)}</p>
      <div className="quality">{Object.entries(snapshot?.latest[stream]?.values ?? {}).map(([name, value]) => <div key={name}><span>{name}</span><strong>{value === null ? 'Unavailable' : String(value)}</strong></div>)}</div>
    </div>)}
    <p className="hint">Channel quality: 0–4. Overall: 0–100. Battery is 0–4 unless a battery-percent field is supplied. Contact quality and EEG quality are different measurements.</p>
  </section>;
}
