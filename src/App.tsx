import { useDashboard } from './hooks/useDashboard';
import { EegChannels } from './components/dashboard/EegChannels';
import { Metrics } from './components/dashboard/Metrics';
import { Quality } from './components/dashboard/Quality';
import { BandPower } from './components/dashboard/BandPower';
import { StreamPanel, streamMessage } from './components/dashboard/StreamPanel';

export default function App() {
  const { snapshot, history, connection, error } = useDashboard();
  const command = snapshot?.latest.com?.values;
  return <main className="dashboard">
    <header className="row wrap"><div><p className="eyebrow">BrainWaves / BrainBot</p><h1>EEG dashboard</h1><p className="hint">Local headset monitoring · genuine Cortex data</p></div>
      <span className={`badge ${connection === 'connected' ? 'online' : 'offline'}`}>Backend {connection}</span></header>
    <section className="status" aria-live="polite"><strong>{snapshot?.status.phase.replaceAll('_', ' ') ?? 'Waiting for backend'}</strong><p>{snapshot?.status.message ?? 'Start the local backend. The dashboard reconnects automatically.'}</p>{snapshot?.headset && <p className="hint">Headset: {snapshot.headset.id}</p>}</section>
    {error && <p className="error" role="alert">{error}</p>}
    <EegChannels snapshot={snapshot} history={history} />
    <div className="columns"><Metrics snapshot={snapshot} /><BandPower snapshot={snapshot} /><Quality snapshot={snapshot} />
      <section className="panel"><h2>Mental command</h2><p className="hint">{streamMessage(snapshot, 'com')}</p><p className="command">{typeof command?.act === 'string' ? command.act : 'Waiting for data'}</p><p>Power: {typeof command?.pow === 'number' ? command.pow.toFixed(2) : 'Unavailable'}</p><p className="hint">Train neutral and an action using EmotivBCI, then load that profile. Commands are displayed only; robot movement is not triggered automatically.</p></section>
    </div>
    <StreamPanel snapshot={snapshot} />
    <section className="panel"><h2>Activity</h2><p className="hint">Malformed samples rejected: {snapshot?.invalid_samples ?? 0}</p>
      <ol className="events">{snapshot?.events.map((event, index) => <li key={`${event.time}-${index}`}><time>{new Date(event.time * 1000).toLocaleTimeString()}</time><span>{event.message}</span></li>)}</ol>
      {!snapshot?.events.length && <p className="empty">Waiting for backend events.</p>}
    </section>
    <footer>Headset → local Cortex WebSocket → Python backend → local WebSocket → dashboard. No EEG recordings are written to disk.</footer>
  </main>;
}
