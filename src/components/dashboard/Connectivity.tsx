import type { Snapshot } from '../../types/dashboard';

export function Connectivity({ snapshot, connection }: { snapshot: Snapshot | null; connection: string }) {
  const services = [
    { name: 'Dashboard backend', status: connection, message: connection === 'connected' ? 'Live dashboard updates connected.' : 'Waiting for the local backend. Reconnecting automatically.' },
    ...(['cortex', 'headset', 'temi'] as const).map(key => ({
      name: { cortex: 'Cortex API', headset: 'EEG headset', temi: 'Temi robot' }[key],
      status: snapshot?.connections[key].status ?? 'unknown',
      message: snapshot?.connections[key].message ?? 'Connection cannot be verified until the backend connects.',
    })),
  ];
  return <section className="connectivity" aria-label="Connection status" aria-live="polite">
    {services.map(service => <article className="panel" key={service.name}>
      <div className="row wrap"><h2>{service.name}</h2><span className={`badge ${service.status === 'connected' ? 'online' : 'offline'}`}>{service.status}</span></div>
      <p className="hint">{service.message}</p>
      {service.name === 'EEG headset' && snapshot?.headset && <p className="hint">Device: {snapshot.headset.id}</p>}
    </article>)}
  </section>;
}
