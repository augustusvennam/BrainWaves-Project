# BrainWaves Project

**Brain–Robot Interaction Demo: "BrainBot: Can you control a robot with your brain?"**

A mood-determining brain demonstration using one Emotiv EPOC X headset wearer. Temi is reserved for emotion display through the Wizard-of-Oz app.

---

## Project Architecture

```
EMOTIV EPOC X (EEG Headset)
    │
    ▼
Emotiv Cortex API (WebSocket: wss://localhost:6868)
    │
    ▼
Python Controller
    ├── brainbot_main.py      # Main integration & interaction flow
    ├── cortex_api_client.py  # Cortex API WebSocket wrapper
    ├── mood_determiner.py    # EEG signal processing & mood classification
    ├── temi_controller.py    # Temi robot communication layer
    └── websocket_server.py   # Real-time data server for frontend
            │
            ▼
        WebSocket (ws://localhost:8080)
            │
            ▼
    React Dashboard (Vite + TypeScript)
    └── src/
        ├── App.tsx           # Main dashboard component
        ├── components/ui/    # UI component library
        │   ├── EEGDashboard.tsx   # Real-time EEG dashboard
        │   ├── EEGGraph.tsx       # Live metric visualization
        │   └── ...              # Other components
        └── services/
            └── websocket.ts    # WebSocket client service
            │
            ▼
    temi-woz-android app (WebSocket: ws://<TEMI_IP>:8175)
            │
            ▼
    Temi Robot Actions (Speak, Ask, Go To)
```

---

## Project Structure

```
BrainWaves Project/
├── README.md                    # This file
├── package.json                 # Frontend dependencies (React, Vite, Recharts)
├── tsconfig.json                # TypeScript configuration
├── tsconfig.node.json           # Node/TypeScript config for tooling
├── vite.config.ts               # Vite build configuration
├── index.html                   # HTML entry point
│
├── src/
│   ├── main.jsx                 # React entry point
│   ├── App.tsx                  # Main dashboard component
│   ├── index.css                # Global styles
│   │
│   ├── components/
│   │   └── ui/                  # UI component library
│   │       ├── EEGDashboard.tsx # Real-time EEG dashboard
│   │       ├── EEGGraph.tsx     # Live metric visualization
│   │       ├── Badge.tsx        # Status badge
│   │       ├── Button.tsx       # Interactive button
│   │       ├── Card.tsx         # Content card
│   │       ├── LogEntry.tsx     # Activity log entry
│   │       ├── Monitor.tsx      # System status monitor
│   │       ├── MilestoneCard.tsx # Project milestone card
│   │       ├── SectionTitle.tsx # Section title
│   │       ├── SectionSubtitle.tsx # Section subtitle
│   │       └── index.ts         # Barrel export
│   │
│   ├── services/
│   │   └── websocket.ts         # WebSocket client service
│   │
│   ├── cortex_api_client.py     # Cortex API WebSocket wrapper
│   ├── mood_determiner.py       # EEG signal processing
│   ├── temi_controller.py       # Temi robot communication
│   ├── brainbot_main.py         # Main backend application
│   ├── websocket_server.py      # WebSocket server for frontend
│   └── config.py                # Configuration loader
│
├── scripts/
│   ├── test_cortex.py           # Cortex API connectivity test
│   └── test_temi.py             # Temi robot connectivity test
│
├── config/
│   └── settings.yaml            # Project configuration
│
├── docs/
│   └── research.md              # Emotiv + Cortex API research notes
│
└── requirements.txt             # Python dependencies
```

---

## Getting Started

### Prerequisites

1. **Emotiv Launcher** installed and running
2. **EPOC X Headset** paired and connected
3. **Python 3.9+** installed
4. **Node.js 18+** installed (for frontend)

### Installation

#### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Install Frontend Dependencies

```bash
npm install
```

#### 3. Configure Settings

Edit `config/settings.yaml` with your Emotiv credentials:

```yaml
emotiv:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  websocket_url: "wss://localhost:6868"

temi:
  robot_ip: "192.168.1.100"  # Your Temi's IP address
  port: 80
```

### Running the Application

#### Option A: Run Both Backend and Frontend (Recommended)

**Terminal 1 — Start Python Backend:**

```bash
python src/brainbot_main.py
```

**Terminal 2 — Start WebSocket Server:**

```bash
python src/websocket_server.py
```

**Terminal 3 — Start Frontend Dev Server:**

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

#### Option B: Run WebSocket Server Only (Frontend + Backend)

If you want real-time data visualization:

```bash
# Start WebSocket server (connects to Cortex)
python src/websocket_server.py

# In another terminal, start frontend
npm run dev
```

#### Option C: Frontend Only (Static Dashboard)

If you just want to see the dashboard without live data:

```bash
npm run dev
```

---

## Testing

### Test Cortex API Connection

```bash
python scripts/test_cortex.py
```

This will:
1. Connect to the Cortex WebSocket server
2. Authenticate with Emotiv credentials
3. Query for connected headsets
4. Create a session and subscribe to streams
5. Exit with non-zero status on any failure

### Test Temi Robot Connection

```bash
python scripts/test_temi.py
```

To run in dry-run mode (skip actual Temi calls):

```bash
TEMI_DRY_RUN=1 python scripts/test_temi.py
```

### Start Development Server

```bash
# Frontend only
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Components

### EEGGraph Component

Renders a live line chart of Cortex performance metrics:

- **Engagement** (`eng`) — blue
- **Excitement** (`exc`) — pink
- **Stress** (`str`) — orange
- **Relaxation** (`rel`) — green
- **Interest** (`int`) — purple
- **Long-term Excitement** (`lex`) — cyan

Each graph shows a rolling window of the last 20 data points with threshold indicators.

### EEGDashboard Component

Main dashboard section that:
- Connects to the WebSocket server
- Displays live metric graphs
- Shows current mood and focus level
- Provides system status monitors

---

## Architecture Details

### Data Flow

1. **EEG Capture**: EPOC X headset captures brainwave data at 128 Hz
2. **Cortex Processing**: Emotiv Cortex API processes raw EEG into:
   - `com`: Mental commands (push, pull, lift, etc.)
   - `met`: Performance metrics (engagement, excitement, stress, etc.)
   - `sys`: System events (connection quality, battery level)
3. **Python Backend**: Receives data via WebSocket, classifies mood, controls robot
4. **WebSocket Server**: Forwards real-time data to frontend clients
5. **React Dashboard**: Visualizes data with live charts and status indicators
6. **Temi Robot**: Executes actions based on brain state (move, turn, dance)

### Streams

- **com (Mental Commands)**: Action + power level (e.g., `["push", 0.7]`)
- **met (Performance Metrics)**: 6 metrics at 0.1 Hz (basic license) or 2 Hz (premium)
- **sys (System Events)**: Connection status, battery level, training events

---

## Design System

The dashboard uses a Linear-inspired design system:

- **Dark mode first** — `--surface-canvas: #010102`
- **Indigo accent** — `--accent: #5e6ad2`
- **4-step surface ladder** — `#010102` → `#0f1011` → `#141516` → `#18191a` → `#191a1b`
- **Hairline borders** — Semi-transparent borders for depth
- **Typography** — Inter for text, JetBrains Mono for code

---

## Notes

- **Mock mode removed**: All backend paths are now real — no simulated data
- **Local hosting**: Dashboard runs on localhost only, no cloud deployment
- **Real-time**: WebSocket connection provides live EEG data visualization
- **Heuristic mood**: Mood classification is heuristic-based, not validated emotion detection
- **License**: Basic license gives 0.1 Hz metric rate; premium unlocks 2 Hz

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **Emotiv** — EPOC X headset and Cortex API
- **Temi** — Mobile robot platform
- **Linear** — Design system inspiration