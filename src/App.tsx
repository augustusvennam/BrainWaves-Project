import { useState } from 'react';
import { Operator, Estimate } from './components/dashboard/Operator';
import { request } from './services/api';
import { Connectivity } from './components/dashboard/Connectivity';
import { useDashboard } from './hooks/useDashboard';
import { EegChannels } from './components/dashboard/EegChannels';
import { Metrics } from './components/dashboard/Metrics';
import { Quality } from './components/dashboard/Quality';
import { BandPower } from './components/dashboard/BandPower';
import { StreamPanel, streamMessage } from './components/dashboard/StreamPanel';

export default function App() {
  const { snapshot, history, connection, error } = useDashboard();
  const [operator, setOperator] = useState(true);
  const [notice, setNotice] = useState('');
  const command = snapshot?.latest.com?.values;
  return <main className="dashboard">
    <header className="row wrap"><div><p className="eyebrow">BrainWaves / BrainBot</p><h1>EEG dashboard</h1><p className="hint">Local headset monitoring · genuine Cortex data</p></div>
      <div className="controls"><button onClick={() => setOperator(!operator)}>{operator ? 'Presentation view' : 'Operator view'}</button><button onClick={async () => {try {if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen();} catch {setNotice('Fullscreen unavailable in this browser.');}}}>Toggle full screen</button><span className={`badge ${connection === 'connected' ? 'online' : 'offline'}`}>Backend {connection}</span></div></header>
    <Connectivity snapshot={snapshot} connection={connection} />
    <section className="status" aria-live="polite"><strong>{snapshot?.status.phase.replaceAll('_', ' ') ?? 'Waiting for backend'}</strong><p>{snapshot?.status.message ?? 'Start the local backend. The dashboard reconnects automatically.'}</p>{snapshot?.headset && <p className="hint">Headset: {snapshot.headset.id}</p>}</section>
    {error && <p className="error" role="alert">{error}</p>}
    {notice && <p role="status">{notice}</p>}
    {snapshot?.recording?.replay && <p className="replay" role="status">Replay — recorded measurements · robot commands disabled</p>}
    {operator && <Operator snapshot={snapshot} />}
    <Estimate snapshot={snapshot} />
    <EegChannels snapshot={snapshot} history={history} />
    <div className="columns"><Metrics snapshot={snapshot} /><BandPower snapshot={snapshot} /><Quality snapshot={snapshot} />
      <section className="panel"><h2>Cortex mental command</h2><p className="hint">{streamMessage(snapshot, 'com')}</p><p className="command">{typeof command?.act === 'string' ? command.act : 'Waiting for data'}</p><p>Power: {typeof command?.pow === 'number' ? command.pow.toFixed(2) : 'Unavailable'}</p><p className="hint">Load a participant profile, train neutral and one action in Operator view or EmotivBCI, then save explicitly. Commands are displayed only; robot movement is not triggered automatically.</p></section>
    </div>
    {operator && <StreamPanel snapshot={snapshot} />}
    <section className="panel"><div className="row"><h2>Activity</h2><button onClick={() => request('/api/events/clear',{}).catch(e => setNotice(e.message))}>Clear activity</button></div><p className="hint">{JSON.stringify(snapshot?.counters ?? {})} · browser feed dropped: {snapshot?.feed_dropped ?? 0}</p><p className="hint">Malformed samples rejected: {snapshot?.invalid_samples ?? 0}</p>
      <ol className="events">{snapshot?.events.map((event, index) => <li key={`${event.time}-${index}`}><time>{new Date(event.time * 1000).toLocaleTimeString()}</time><span>{event.message}</span></li>)}</ol>
      {!snapshot?.events.length && <p className="empty">Waiting for backend events.</p>}
    </section>
    <footer>Headset → local Cortex WebSocket → Python backend → local WebSocket → dashboard. Recording is off by default and requires participant consent.</footer>
  </main>;
}
