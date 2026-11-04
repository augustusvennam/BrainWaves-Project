import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import Card, { CardBody, CardHeader } from './Card';
import Badge from './Badge';
import { SectionTitle } from './SectionTitle';
import { EEGGraph, EEG_METRICS } from './EEGGraph';
import { websocketService, backendUrl, type ConnectionStatus } from '../../services/websocket';

type Values = Record<string, unknown>;
const BANDS = ['theta', 'alpha', 'betaL', 'betaH', 'gamma'] as const;
const COLORS = ['#60a5fa', '#34d399', '#fbbf24', '#fb923c', '#f472b6'];
const COMMAND_STATES = [
  { id: 'neutral', label: 'Calm (Neutral)', color: '#94a3b8' },
  { id: 'push', label: 'Happy (Push)', color: '#97ec48' },
  { id: 'pull', label: 'Sad (Pull)', color: '#60a5fa' },
  { id: 'lift', label: 'Angry (Lift)', color: '#ff3333' },
  { id: 'drop', label: 'Anxious (Drop)', color: '#e040d3' },
] as const;

function object(value: unknown): Values {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Values : {};
}

export function EEGDashboard({ wsUrl = backendUrl() }: { wsUrl?: string }) {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<Values>({});
  const [bands, setBands] = useState<Values[]>([]);
  const [lastBackend, setLastBackend] = useState(0);
  const [now, setNow] = useState(Date.now());
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  useEffect(() => {
    const offConnect = websocketService.onConnect(() => setConnected(true));
    const offDisconnect = websocketService.onDisconnect(() => {
      setConnected(false); setState({}); setBands([]);
    });
    const offStatus = websocketService.onStatus(setStatus);

    const offMessage = websocketService.onMessage(message => {
      setLastBackend(Date.now());

      if (message.type === 'state') {
        setState(message.data);
        if (!message.data.cortex_connected) setBands([]);
      }

      if (message.type === 'pow') {
        const row: Values = { time: new Date(Number(message.data.sample_time) * 1000).toLocaleTimeString() };

        for (const band of BANDS) {
          const values = Object.entries(message.data)
            .filter(([key, value]) => key.endsWith(`/${band}`) && typeof value === 'number' && Number.isFinite(value))
            .map(([, value]) => value as number);
          row[band] = values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
        }

        setBands(previous => [...previous.slice(-239), row]);
      }
    });

    const timer = setInterval(() => setNow(Date.now()), 1000);
    websocketService.connect(wsUrl);

    return () => {
      offConnect(); offDisconnect(); offMessage(); offStatus(); clearInterval(timer);
      websocketService.disconnect();
    };

  }, [wsUrl]);

  const backendFresh = connected && now - lastBackend < 5000;
  const times = object(state.last_sample_time);
  const quality = object(state.quality);
  const device = object(state.device);
  const command = object(state.command);
  const commandAge = typeof times.com === 'number' ? Math.max(0, Math.floor(now / 1000 - times.com)) : null;
  const bandAge = typeof times.pow === 'number' ? now / 1000 - times.pow : Infinity;
  const activeCommand = backendFresh && state.cortex_connected && commandAge !== null && commandAge <= 5
    ? String(command.act || '') : '';
  return <div className="space-y-6">
    <div className="flex flex-wrap gap-3 items-center">
      <Badge label={backendFresh ? 'Backend connected' : 'Backend unavailable'} variant={backendFresh ? 'online' : 'warning'} dot />
      <Badge label={backendFresh && state.cortex_connected ? 'Cortex streaming' : 'Cortex unavailable'} variant={backendFresh && state.cortex_connected ? 'online' : 'warning'} dot />
      <Badge
        label={status === 'connected' ? 'Connected' : status === 'connecting' ? 'Reconnecting…' : 'Disconnected'}
        variant={status === 'connected' ? 'online' : status === 'connecting' ? 'warning' : 'error'}
        dot
      />
      <span className="text-sm text-[var(--text-subtle)]">{backendFresh ? String(state.status || 'Waiting') : 'Waiting for backend heartbeat'}</span>
    </div>
    <Card><CardHeader><SectionTitle>Current Mood</SectionTitle></CardHeader>
      <CardBody>
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
          {COMMAND_STATES.map((state_item) => {
            const isActive = activeCommand === state_item.id;
            return (
              <div
                key={state_item.id}
                className="rounded-[var(--radius-lg)] border p-4 text-center"
                style={{
                  borderColor: isActive ? state_item.color : 'var(--border-default)',
                  background: isActive ? `${state_item.color}15` : 'var(--surface-1)',
                }}
              >
                <div
                  className="text-2xl font-medium tracking-tight"
                  style={{ color: isActive ? state_item.color : 'var(--text-muted)' }}
                >
                  {state_item.label}
                </div>
                <div className="mt-1 text-xs text-[var(--text-tertiary)]">
                  {isActive ? `active · power ${Number(command.pow).toFixed(2)}` : 'idle'}
                </div>
              </div>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-[var(--text-tertiary)]">
          Mental commands sample at 8 Hz from the EMOTIV BCI profile. {commandAge === null ? 'No command received yet.' : `Last command ${commandAge}s ago.`}
        </p>
      </CardBody></Card>
    <Card>
      <CardHeader><SectionTitle>System status</SectionTitle></CardHeader>
      <CardBody>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">EEG quality</div>
            <div className="mt-1 text-lg font-medium">
              {backendFresh && state.cortex_connected && typeof quality.overall === 'number' ? `${quality.overall}%` : 'Unavailable'}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Battery</div>
            <div className="mt-1 text-lg font-medium">
              {backendFresh && state.cortex_connected && typeof device.BatteryPercent === 'number' ? `${device.BatteryPercent}%` : 'Unavailable'}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">Temi</div>
            <div className="mt-1 text-lg font-medium">
              {backendFresh && state.temi_connected ? 'Connected' : 'Disabled or unavailable'}
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
    <section><SectionTitle>Performance metrics</SectionTitle>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
        {EEG_METRICS.map(metric => <EEGGraph key={metric.metric} metric={metric.metric} title={metric.title} color={metric.color} />)}
      </div></section>
    <Card><CardHeader><SectionTitle>Frequency-band power</SectionTitle></CardHeader>
      <CardBody>
        <p className="text-sm text-[var(--text-subtle)] mb-3">Mean across available channels, µV²/Hz. Cortex band powers update at 8 Hz; this is derived activity, not a raw EEG waveform.</p>
        {backendFresh && bandAge < 5 && bands.length ? <ResponsiveContainer width="100%" height={240}>
          <LineChart data={bands}><XAxis dataKey="time" minTickGap={60} /><YAxis /><Tooltip contentStyle={{ background: '#010102', border: '1px solid var(--border-hairline)', borderRadius: '8px', color: 'var(--text-ink)' }} />
            {BANDS.map((band, i) => <Line key={band} dataKey={band} stroke={COLORS[i]} dot={false} isAnimationActive={false} connectNulls={false} />)}
          </LineChart>
        </ResponsiveContainer> : <p className="py-8 text-center">Waiting for fresh frequency-band samples…</p>}
        <div className="flex flex-wrap gap-4 text-xs">{BANDS.map((band, i) => <span key={band} className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: COLORS[i] }} /><span style={{ color: COLORS[i] }}>{band}</span></span>)}</div>
      </CardBody></Card>
  </div>;
}
export default EEGDashboard;
