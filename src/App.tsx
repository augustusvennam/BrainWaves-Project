/**
 * BrainWaves Project — BrainBot Dashboard
 * Real-time EEG monitoring UI with Linear design system.
 *
 * Architecture: EPOC X → Cortex API → Python brainbot_main.py → Temi Robot
 *
 * Data streams from Cortex:
 *   - `met`, `pow`, `dev`, `eq` (Basic BCI streams)
 *
 * The dashboard connects to a local Python WebSocket server for live data.
 * Run `python -m src.websocket_server` to start the backend.
 */

/**
 * BrainWaves Project — BrainBot Dashboard
 * Real-time EEG monitoring UI with Linear design system.
 *
 * Architecture: EPOC X → Cortex API → Python brainbot_main.py → Temi Robot
 *
 * Data streams from Cortex:
 *   - `met`, `pow`, `dev`, `eq` (Basic BCI streams)
 *
 * The dashboard connects to a local Python WebSocket server for live data.
 * Run `python -m src.websocket_server` to start the backend.
 */

import { Badge, EEGDashboard } from './components/ui';

/**
 * App — Main dashboard composition
 *
 * Sections (mobile-first, breakpoints 640/768/1024/1280):
 *  1. Header — project name + live connection status badges
 *  2. Current Mood — 5 state cards for brain monitoring
 *  3. System Status — EEG quality, Battery, Temi connection
 *  4. Performance Metrics — 6 metric charts
 *  5. Frequency-band power — 5 bands line chart
 */

function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', fontFamily: 'var(--font-text)' }}>
      <div className="container">

        {/* ===== HEADER ===== */}
        <header className="card-elevated mb-8 border-b border-[var(--border-hairline)] pb-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-medium text-[var(--text-ink)]">
                BrainWaves Project
              </h1>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge label="Local Host: Network Limited" variant="info" dot={false} />
            </div>
          </div>
        </header>

        {/* ===== CURRENT MOOD ===== */}
        <section className="mb-10">
          <EEGDashboard />
        </section>

      </div>
    </div>
  );
}

export default App;