import { useState } from 'react';
import type { Snapshot } from '../../types/dashboard';
import { streamMessage } from './StreamPanel';
export function BandPower({ snapshot }: { snapshot: Snapshot | null }) {
  const [selected, setSelected] = useState('');
  const values = snapshot?.latest.pow?.values ?? {};
  const channels = [...new Set(Object.keys(values).map(key => key.split('/')[0]))];
  const channel = channels.includes(selected) ? selected : channels[0] ?? '';
  const bands = Object.entries(values).filter(([key, value]) => key.startsWith(`${channel}/`) && typeof value === 'number');
  const max = Math.max(1, ...bands.map(([, value]) => value as number));
  return <section className="panel"><div className="row"><h2>Frequency-band power</h2>{channels.length > 0 && <select aria-label="Band power channel" value={channel} onChange={event => setSelected(event.target.value)}>{channels.map(name => <option key={name}>{name}</option>)}</select>}</div>
    <p className="hint">{streamMessage(snapshot, 'pow')}</p>
    {bands.length ? <div className="metrics">{bands.map(([key, value]) => <div key={key}><div className="row"><span>{key.split('/')[1]}</span><strong>{(value as number).toFixed(3)} µV²/Hz</strong></div><meter min={0} max={max} value={value as number} aria-label={key} /></div>)}</div> : <p className="empty">No band-power stream received.</p>}
    <p className="hint">Values are supplied by Cortex: theta 4–8, alpha 8–12, betaL 12–16, betaH 16–25, gamma 25–45 Hz. Cortex uses a two-second window. Delta is not supplied or calculated here.</p>
  </section>;
}
