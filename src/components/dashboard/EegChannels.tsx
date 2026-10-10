import { useEffect, useMemo, useState } from 'react';
import type { EegSample, Snapshot } from '../../types/dashboard';
import { Waveform } from './Waveform';
import { streamMessage } from './StreamPanel';
const FIXED_SCALE: [number, number] = [0, 8000];
export function EegChannels({ snapshot, history }: { snapshot: Snapshot | null; history: EegSample[] }) {
  const [selected, setSelected] = useState('');
  const [all, setAll] = useState(false);
  const [seconds, setSeconds] = useState(10);
  const [scale, setScale] = useState('automatic');
  const [paused, setPaused] = useState<EegSample[] | null>(null);
  const [filtered, setFiltered] = useState(false);
  const [filteredHistory, setFilteredHistory] = useState<EegSample[]>([]);
  useEffect(() => {setPaused(null); setFilteredHistory([]);}, [snapshot?.epoch]);
  useEffect(() => {
    if (!snapshot?.recording?.filter.enabled) {setFilteredHistory([]); return;}
    setFilteredHistory(previous => {
      const last = previous.at(-1)?.time ?? -Infinity;
      return [...previous, ...(snapshot?.filtered_eeg ?? []).filter(s => s.time > last)].slice(-16384);
    });
  }, [snapshot?.filtered_eeg, snapshot?.recording?.filter.enabled]);
  const shown = paused ?? (filtered ? filteredHistory : history);
  const common = useMemo<[number, number] | undefined>(() => {
    const amplitudes = shown.slice(-1024).flatMap(s => Object.values(s.values));
    return amplitudes.length ? [Math.min(...amplitudes)-1, Math.max(...amplitudes)+1] : undefined;
  }, [shown]);
  const channels = Object.keys(history.at(-1)?.values ?? {});
  const channel = channels.includes(selected) ? selected : channels[0] ?? '';
  const age = snapshot?.streams.eeg?.age_seconds;
  return <section className="panel"><div className="row wrap"><div><h2>Live EEG waveforms</h2><p className="hint">{filtered ? 'Filtered amplitude' : 'Raw amplitude'} · µV · configurable window · bounded history</p></div>
    {channels.length > 0 && <div className="row"><select aria-label="EEG channel" value={channel} onChange={event => setSelected(event.target.value)}>{channels.map(name => <option key={name}>{name}</option>)}</select><label><input type="checkbox" checked={all} onChange={event => setAll(event.target.checked)} /> All channels</label></div>}</div>
    <div className="controls"><button onClick={() => setPaused(paused ? null : [...shown])}>{paused ? 'Resume waveforms' : 'Pause waveforms'}</button><label>Time window<select aria-label="Time window" value={seconds} onChange={e => setSeconds(Number(e.target.value))}>{[2,5,10,30].map(n => <option key={n} value={n}>{n} seconds</option>)}</select></label><label>Vertical scale<select aria-label="Vertical scale" value={scale} onChange={e => setScale(e.target.value)}><option value="automatic">Automatic per trace</option><option value="fixed">Fixed 0–8000 µV</option><option value="common">Common across channels</option></select></label><label><input type="checkbox" checked={filtered} disabled={!snapshot?.recording?.filter.enabled} onChange={e => {setFiltered(e.target.checked);setPaused(null);}}/> Filtered view</label></div>
    {filtered && <p className="hint">{snapshot?.recording?.filter.settings}</p>}
    <p className="hint">{streamMessage(snapshot, 'eeg')}</p>
    {age !== null && age !== undefined && age > 2 && <p className="warning">EEG data is stale. Traces show the last received samples.</p>}
    {!channels.length ? <p className="empty">Waiting for genuine EEG samples. Raw EEG requires an appropriate Emotiv license and an <code>eeg</code> subscription.</p> : (all ? channels : [channel]).map(name => <div className="channel" key={name}><h3>{name}</h3><Waveform samples={shown} channel={name} seconds={seconds} filtered={filtered} scale={scale === 'fixed' ? FIXED_SCALE : scale === 'common' ? common : undefined} /></div>)}
    <p className="hint">History is capped at 16,384 samples. {history.length} samples retained; {history.filter(sample => sample.interpolated).length} flagged as interpolated by Cortex. Raw measurements remain available independently of the optional filtered view.</p>
  </section>;
}
