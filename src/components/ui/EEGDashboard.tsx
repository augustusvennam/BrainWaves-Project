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
import {
  Card,
  CardHeader,
  CardBody,
  Monitor,
  Badge,
  SectionTitle,
  SectionSubtitle,
  EEGGraph,
  EEG_METRICS,
} from '.';
import { websocketService } from '../../services/websocket';
import { Brain, Server, Bot, Activity } from 'lucide-react';

type MonitorStatus = 'online' | 'offline' | 'idle' | 'connecting';

interface MonitorState {
  id: string;
  title: string;
  status: MonitorStatus;
  detail: string;
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
    status: 'offline',
    detail: 'Waiting for Temi on network...',
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
          break;

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