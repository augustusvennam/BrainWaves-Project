import { useState } from 'react';
import type { EegSample, Snapshot } from '../../types/dashboard';
import { Waveform } from './Waveform';
import { streamMessage } from './StreamPanel';
export function EegChannels({ snapshot, history }: { snapshot: Snapshot | null; history: EegSample[] }) {
  const [selected, setSelected] = useState('');
  const [all, setAll] = useState(false);
  const channels = Object.keys(history.at(-1)?.values ?? {});
  const channel = channels.includes(selected) ? selected : channels[0] ?? '';
  const age = snapshot?.streams.eeg?.age_seconds;
  return <section className="panel"><div className="row wrap"><div><h2>Live EEG waveforms</h2><p className="hint">Raw amplitude · µV · rolling 10 seconds · automatic vertical scale</p></div>
    {channels.length > 0 && <div className="row"><select aria-label="EEG channel" value={channel} onChange={event => setSelected(event.target.value)}>{channels.map(name => <option key={name}>{name}</option>)}</select><label><input type="checkbox" checked={all} onChange={event => setAll(event.target.checked)} /> All channels</label></div>}</div>
    <p className="hint">{streamMessage(snapshot, 'eeg')}</p>
    {age !== null && age !== undefined && age > 2 && <p className="warning">EEG data is stale. Traces show the last received samples.</p>}
    {!channels.length ? <p className="empty">Waiting for genuine EEG samples. Raw EEG requires an appropriate Emotiv license and an <code>eeg</code> subscription.</p> : (all ? channels : [channel]).map(name => <div className="channel" key={name}><h3>{name}</h3><Waveform samples={history} channel={name} /></div>)}
    <p className="hint">History is capped at 4,096 samples. {history.length} samples retained; {history.filter(sample => sample.interpolated).length} flagged as interpolated by Cortex. No filtering or derived mood values are applied.</p>
  </section>;
}
