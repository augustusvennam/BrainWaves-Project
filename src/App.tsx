/**
 * BrainWaves Project — BrainBot Dashboard
 * Real-time EEG monitoring UI with Linear design system.
 *
 * Architecture: EPOC X → Cortex API → Python brainbot_main.py → Temi Robot
 *
 * Data streams from Cortex:
 *   - `com` (mental commands)
 *   - `met` (mood metrics)
 *   - `sys` (system events)
 *
 * The dashboard connects to a local Python WebSocket server for live data.
 * Run `python src/brainbot_main.py` to start the backend.
 */

import React, { useState } from 'react';
import { Server, Bot, Brain } from 'lucide-react';
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardBody,
  Monitor,
  LogEntry,
  MilestoneCard,
  SectionTitle,
  SectionSubtitle,
  ArchitectureDiagram,
  EEGDashboard,
} from './components/ui';
import { type ReactNode } from 'react';

// Type definitions
type MilestoneStatus = 'complete' | 'in-progress' | 'pending';
type MonitorStatus = 'online' | 'offline' | 'idle' | 'connecting';

// Default milestone data
const defaultMilestones: Record<string, MilestoneStatus> = {
  structure: 'complete',
  'cortex-research': 'complete',
  'temi-research': 'complete',
  framework: 'in-progress',
  'cortex-creds': 'pending',
  hardware: 'pending',
};

// Default monitor data
interface MonitorState {
  id: string;
  title: string;
  status: MonitorStatus;
  detail: string;
  icon: ReactNode;
}

const defaultMonitors: Record<string, MonitorState> = {
  cortex: { id: 'cortex', title: 'Cortex API Connection', status: 'connecting', detail: 'Connecting to wss://localhost:6868...', icon: Server },
  temi: { id: 'temi', title: 'Temi Robot Connection', status: 'offline', detail: 'Waiting for Temi on network...', icon: Bot },
  mood: { id: 'mood', title: 'Mood Detection Engine', status: 'idle', detail: 'Awaiting met stream data...', icon: Brain },
};

// Default activity log entries
const defaultLogs = [
  { id: 1, time: new Date().toISOString().replace('T', ' ').slice(0, 19), level: 'info', message: 'BrainWaves Project dashboard initialized' },
  { id: 2, time: new Date().toISOString().replace('T', ' ').slice(0, 19), level: 'info', message: 'Configure credentials in config/settings.yaml' },
  { id: 3, time: new Date().toISOString().replace('T', ' ').slice(0, 19), level: 'info', message: 'Start brainbot_main.py when hardware is ready' },
];

/**
 * App — Main dashboard composition
 *
 * Sections (mobile-first, breakpoints 640/768/1024/1280):
 *  1. Header — project name + live connection status badges
 *  2. Real-Time EEG Dashboard — live metric graphs + system monitors
 *  3. Project Progress — 6 milestone cards with status transitions
 *  4. Activity Log — timestamped, color-coded entries (info/warn/error)
 *  5. Architecture Diagram — horizontal flow: EPOC X → Cortex → Python → Temi
 */

function App() {
  const [monitors] = useState<MonitorState[]>(() => Object.values(defaultMonitors));
  const [milestones] = useState<Record<string, MilestoneStatus>>(() => ({ ...defaultMilestones }));
  const [logs] = useState<{ id: number; time: string; level: 'info' | 'warn' | 'error'; message: string }[]>(() => [...defaultLogs]);

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', fontFamily: 'var(--font-text)' }}>
      <div className="container">

        {/* ===== HEADER ===== */}
        <header className="card-elevated mb-6 border-b border-[var(--border-default)] pb-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <Badge label="brain" variant="info" dot={false} />
              <h1 className="text-xl font-medium text-[var(--text-ink)] tracking-tighter">
                BrainWaves Project
              </h1>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge label="Localhost" variant="info" dot={false} />
              {monitors.map((m) => (
                <Badge key={m.id} label={m.status} variant={statusVariant(m.status)} dot={false} />
              ))}
            </div>
          </div>
        </header>

        {/* ===== REAL-TIME EEG DASHBOARD ===== */}
        <section className="mb-8">
          <EEGDashboard wsUrl="ws://localhost:8080" />
        </section>

        {/* ===== PROJECT PROGRESS ===== */}
        <section className="mb-6">
          <SectionTitle>Project Progress</SectionTitle>
          <SectionSubtitle>
            6 milestones — {Object.values(milestones).filter(s => s === 'complete').length} complete,{' '}
            {Object.values(milestones).filter(s => s === 'in-progress').length} in progress,{' '}
            {Object.values(milestones).filter(s => s === 'pending').length} pending
          </SectionSubtitle>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {Object.entries(milestones).map(([id, status]) => {
              const fallbackMap: Record<string, { title: string; desc: string }> = {
                structure: { title: 'Project structure created', desc: 'Repository layout, Vite config, component scaffolding' },
                'cortex-research': { title: 'Cortex API research', desc: 'EMOTIV Cortex WebSocket API (wss://localhost:6868)' },
                'temi-research': { title: 'Temi integration research', desc: 'Temi robot SDK + navigation/movement APIs' },
                framework: { title: 'Base framework ready', desc: 'React + Vite dashboard shell' },
                'cortex-creds': { title: 'Cortex API credentials', desc: 'Register at emotiv.com/my-account → Cortex Apps' },
                hardware: { title: 'Hardware testing', desc: 'Awaiting EPOC X device for validation' },
              };
              const fb = fallbackMap[id] || { title: id, desc: '' };
              return (
                <MilestoneCard
                  key={id}
                  id={id}
                  title={fb.title}
                  description={fb.desc}
                  status={status}
                  onClick={() => {}}
                />
              );
            })}
          </div>
        </section>

        {/* ===== SYSTEM STATUS ===== */}
        <section className="mb-6">
          <SectionTitle>System Status</SectionTitle>
          <SectionSubtitle>Real-time infrastructure health monitors</SectionSubtitle>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
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

        {/* ===== ACTIVITY LOG ===== */}
        <section className="mb-6">
          <SectionTitle>Activity Log</SectionTitle>
          <SectionSubtitle>Chronological project milestones and system events</SectionSubtitle>

          <div className="rounded-[var(--radius-lg)] bg-[var(--surface-1)] border border-[var(--border-default)] overflow-hidden">
            <div className="px-4 py-3 border-b border-[var(--border-hairline)]">
              <span className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider">Log entries</span>
            </div>
            <div className="px-4 py-2">
              <button className="text-xs text-[var(--accent)] hover:underline">Clear</button>
            </div>
          </div>

          <div className="mt-3 rounded-[var(--radius-lg)] bg-[var(--surface-1)] border border-[var(--border-default)]">
            <div className="px-4 py-2" style={{ maxHeight: '320px', overflowY: 'auto' }}>
              {logs.map((entry) => (
                <LogEntry
                  key={entry.id}
                  id={entry.id}
                  time={entry.time}
                  level={entry.level}
                  message={entry.message}
                />
              ))}
            </div>
          </div>
        </section>

        {/* ===== ARCHITECTURE DIAGRAM ===== */}
        <section className="pt-4">
          <SectionTitle>Architecture</SectionTitle>
          <SectionSubtitle>Data flow: EEG capture → real-time streaming → brainwave processing → robot control</SectionSubtitle>
          <ArchitectureDiagram />
          <div className="mt-4 pt-4 border-t border-[var(--border-hairline)] text-xs text-[var(--text-tertiary)]">
            <strong>Note:</strong> Architecture diagram reflects live data flow. Connection status updates in real time as monitors change state.
          </div>
        </section>

      </div>
    </div>
  );
}

function statusVariant(status: MonitorStatus): 'online' | 'offline' | 'idle' | 'warning' {
  switch (status) {
    case 'online': return 'online';
    case 'offline': return 'offline';
    case 'idle': return 'idle';
    case 'connecting': return 'warning';
    default: return 'offline';
  }
}

export default App;