/**
 * EEGDashboard — Real-time EEG monitoring dashboard.
 *
 * Combines live EEG metric graphs with system status monitors.
 * Connects to the Python BrainBot backend via WebSocket.
 *
 * Props:
 *   wsUrl  - WebSocket URL of the Python backend (default: ws://localhost:8080)
 */

import { useState, useEffect, useCallback } from 'react';
import Card, { CardHeader, CardBody } from './Card';
import Badge from './Badge';
import Monitor from './Monitor';
import { SectionTitle } from './SectionTitle';
import { SectionSubtitle } from './SectionSubtitle';
import { EEGGraph, EEG_METRICS } from './EEGGraph';
import { websocketService } from '../../services/websocket';
import { Brain, Server, Bot, Activity } from 'lucide-react';

type MonitorStatus = 'online' | 'offline' | 'idle' | 'connecting';

interface MonitorState {
  id: string;
  title: string;
  status: MonitorStatus;
  detail: string;
  icon: React.ReactNode;
}

const defaultMonitors: MonitorState[] = [
  {
    id: 'cortex',
    title: 'Cortex API Connection',
    status: 'connecting',
    detail: 'Connecting to wss://localhost:6868...',
    icon: <Server className="h-5 w-5" />,
  },
  {
    id: 'mood',
    title: 'Mood Detection Engine',
    status: 'idle',
    detail: 'Awaiting met stream data...',
    icon: <Brain className="h-5 w-5" />,
  },
  {
    id: 'temi',
    title: 'Temi Robot Connection',
    status: 'connecting',
    detail: 'Checking Temi WebSocket...',
    icon: <Bot className="h-5 w-5" />,
  },
];

interface EEGDashboardProps {
  wsUrl?: string;
}

export function EEGDashboard({ wsUrl = 'ws://localhost:8080' }: EEGDashboardProps) {
  const [monitors, setMonitors] = useState<MonitorState[]>(defaultMonitors);
  const [connected, setConnected] = useState(false);
  const [mood, setMood] = useState<string>('Neutral');
  const [focus, setFocus] = useState<number>(0);
  const [eegSamples, setEegSamples] = useState<number[]>([]);
  const [eegAvailable, setEegAvailable] = useState(false);

  // Update a single monitor by id
  const updateMonitor = useCallback((id: string, updates: Partial<MonitorState>) => {
    setMonitors((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  }, []);

  useEffect(() => {
    let isMounted = true;

    websocketService.onConnect(() => {
      if (!isMounted) return;
      setConnected(true);
      updateMonitor('cortex', {
        status: 'online',
        detail: 'Connected to Python backend',
      });
    });

    websocketService.onDisconnect(() => {
      if (!isMounted) return;
      setConnected(false);
      updateMonitor('cortex', {
        status: 'connecting',
        detail: 'Reconnecting to backend...',
      });
    });

    websocketService.onMessage((message) => {
      if (!isMounted) return;

      switch (message.type) {
        case 'state':
        case 'met':
          if (message.data.primary_mood) {
            setMood(String(message.data.primary_mood));
            updateMonitor('mood', {
              status: 'online',
              detail: `Detected: ${message.data.primary_mood}`,
            });
          }
          if (message.data.focus_level !== undefined) {
            setFocus(Number(message.data.focus_level));
          }
          if (message.data.temi_connected !== undefined) {
            const temiConnected = Boolean(message.data.temi_connected);
            updateMonitor('temi', {
              status: temiConnected ? 'online' : 'offline',
              detail: temiConnected
                ? 'Connected to temi-woz-android'
                : 'Temi WebSocket is unreachable',
            });
          }
          if (message.data.eeg_available !== undefined) {
            setEegAvailable(Boolean(message.data.eeg_available));
          }
          break;
        case 'eeg': {
          const sample = message.data.sample;
          if (Array.isArray(sample)) {
            const values = sample.filter((value): value is number => typeof value === 'number');
            if (values.length > 0) {
              setEegSamples(values);
              setEegAvailable(true);
            }
          }
          break;
        }

        case 'sys':
          if (message.data.type === 'connectionLost') {
            updateMonitor('cortex', {
              status: 'offline',
              detail: 'Headset connection lost',
            });
          }
          break;

        case 'com':
          // Mental command received — could update a monitor
          break;

        default:
          break;
      }
    });

    websocketService.connect(wsUrl);

    return () => {
      isMounted = false;
      websocketService.disconnect();
    };
  }, [wsUrl, updateMonitor]);

  return (
    <div className="space-y-6">
      {/* ===== Connection Status ===== */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Badge
            label={connected ? 'Live' : 'Connecting'}
            variant={connected ? 'online' : 'warning'}
            dot
          />
          <span className="text-sm text-[var(--text-subtle)]">
            EEG Dashboard — {connected ? 'Receiving real-time data' : 'Attempting to connect...'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Badge label={`Mood: ${mood}`} variant="info" dot={false} />
          <Badge label={`Focus: ${focus.toFixed(2)}`} variant="info" dot={false} />
        </div>
      </div>

      {/* ===== System Monitors ===== */}
      <section>
        <SectionTitle>System Status</SectionTitle>
        <SectionSubtitle>Real-time infrastructure health monitors</SectionSubtitle>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-3">
          {monitors.map((m) => (
            <Monitor
              key={m.id}
              id={m.id}
              title={m.title}
              status={m.status}
              detail={m.detail}
              icon={m.icon}
            />
          ))}
        </div>
      </section>

      {/* ===== EEG Metric Graphs ===== */}
      <section>
        <SectionTitle>Real-Time EEG Metrics</SectionTitle>
        <SectionSubtitle>
          Live Cortex performance metrics streamed from the EPOC X headset
        </SectionSubtitle>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
          {EEG_METRICS.map((metric) => (
            <EEGGraph
              key={metric.metric}
              metric={metric.metric}
              title={metric.title}
              color={metric.color}
              threshold={metric.threshold}
            />
          ))}
        </div>
      </section>

      <section>
        <SectionTitle>Live EEG Signal</SectionTitle>
        <SectionSubtitle>
          {eegAvailable
            ? 'Raw channel sample from the EPOC X headset'
            : 'Raw EEG is unavailable; enable the Cortex raw EEG license to display the signal'}
        </SectionSubtitle>
        <div className="mt-3 rounded-[var(--radius-lg)] border border-[var(--border-default)] bg-[var(--surface-1)] p-4">
          {eegSamples.length > 1 ? (
            <svg viewBox="0 0 700 180" className="w-full" role="img" aria-label="Live EEG signal">
              <polyline
                fill="none"
                stroke="var(--accent)"
                strokeWidth="2"
                points={eegSamples.map((value, index) => {
                  const min = Math.min(...eegSamples);
                  const max = Math.max(...eegSamples);
                  const range = max - min || 1;
                  return `${(index / (eegSamples.length - 1)) * 700},${170 - ((value - min) / range) * 150}`;
                }).join(' ')}
              />
            </svg>
          ) : (
            <div className="py-8 text-center text-sm text-[var(--text-subtle)]">
              Waiting for raw EEG samples from Cortex…
            </div>
          )}
        </div>
      </section>

      {/* ===== Mood Summary ===== */}
      <section>
        <SectionTitle>Mood Summary</SectionTitle>
        <SectionSubtitle>Current detected emotional state</SectionSubtitle>
        <Card className="mt-3">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-[var(--accent)]" />
              <span className="text-[13px] font-medium text-[var(--text-ink)]">
                Current Mood
              </span>
            </div>
          </CardHeader>
          <CardBody>
            <div className="flex items-baseline gap-3">
              <span className="text-3xl font-medium text-[var(--text-ink)]">{mood}</span>
              <span className="text-sm text-[var(--text-subtle)]">
                Focus Level: {focus.toFixed(2)}
              </span>
            </div>
            <p className="mt-2 text-xs text-[var(--text-tertiary)]">
              Mood is classified from live Cortex performance metrics (eng, exc, str, rel, int, lex).
              This is a heuristic, not validated emotion detection.
            </p>
          </CardBody>
        </Card>
      </section>
    </div>
  );
}

export default EEGDashboard;