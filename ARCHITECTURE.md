# BrainWaves — Architecture

Current system map: EMOTIV EPOC X → Cortex → Python backend → React dashboard, with optional
Temi speech. Dark theme, matching the project's original architecture diagram style.

```mermaid
%%{init: {'theme':'dark', 'flowchart': {'htmlLabels': true, 'curve': 'basis'}}}%%
flowchart TD
    %% ===== Headset =====
    subgraph HEADSET ["EMOTIV EPOC X"]
        direction LR
        EPOC["EPOC X Headset<br/>14 channels · 128 Hz<br/>raw EEG over BLE"]
    end

    %% ===== Cortex service =====
    CORTEX["EMOTIV Cortex Launcher<br/>━━━━━━━━━━━━━━━━━━<br/>wss://localhost:6868<br/>JSON-RPC 2.0 · TLS verified<br/>decodes headset → streams"]

    %% ===== Laptop: Python backend =====
    subgraph LAPTOP ["LAPTOP"]
        direction TB

        CFG["config.py<br/>━━━━━━━━━━━━━━<br/>loads config/settings.yaml<br/>+ .env (gitignored)<br/>→ merged config dict"]

        CLIENT["cortex_api_client.py<br/>━━━━━━━━━━━━━━━━━━━━━━<br/>CortexClient<br/>single socket reader thread<br/>callbacks never call RPC<br/>TLS cert + hostname always on"]

        SERVER["websocket_server.py<br/>━━━━━━━━━━━━━━━━━━━━━━<br/>EEGWebSocketServer<br/>4 asyncio tasks:<br/>acquisition · process<br/>heartbeat · temi_health<br/>ws://127.0.0.1:8080"]

        MOOD["mood_determiner.py<br/>━━━━━━━━━━━━━━━━━━<br/>MoodDeterminer<br/>quality-gated windowed<br/>classifier (heuristic, not probability)<br/>consumes met + eq"]

        TEMICTRL["temi_controller.py<br/>━━━━━━━━━━━━━━━━━━<br/>TemiController<br/>fresh WS per speak()<br/>matches UUID completion ID<br/>sends ≠ completes"]

        ALIAS["brainbot_main.py<br/>━━━━━━━━━━━━━━━━<br/>alias: from src.websocket_server<br/>import main — do not run both"]
    end

    %% ===== Browser =====
    BROWSER["React Dashboard<br/>━━━━━━━━━━━━━━━━━━<br/>Vite dev · http://127.0.0.1:3000<br/>EEGDashboard (connection owner)<br/>EEGGraph x6 (subscribe independently)<br/>websocket.ts singleton<br/>reconnect: 1s→2s→4s→8s→10s cap"]

    %% ===== Temi robot =====
    TEMI["Temi Robot<br/>━━━━━━━━━━━━━━━━━━<br/>Wizard-of-Oz Android app<br/>ws://&lt;TEMI_IP&gt;:8175<br/>speech-only · no movement"]

    %% ===== Flows =====
    EPOC -->|"raw EEG<br/>BLE"| CORTEX
    CORTEX -->|"JSON-RPC 2.0<br/>met · pow · dev · eq · com"| CLIENT

    CFG -->|"config dict"| CLIENT
    CFG -->|"config dict"| SERVER

    CLIENT -->|"call_soon_threadsafe<br/>→ asyncio.Queue (max 512)"| SERVER

    SERVER -->|"ws://127.0.0.1:8080<br/>state (1Hz) · met · pow<br/>dev · eq · com · pong"| BROWSER
    BROWSER -->|"reset_assessment · ping"| SERVER

    SERVER -->|"speak()<br/>asyncio.to_thread<br/>(off Cortex reader)"| TEMICTRL
    TEMICTRL -->|"ws://&lt;TEMI_IP&gt;:8175"| TEMI

    ALIAS -.->|"import"| SERVER

    %% ===== Styling =====
    classDef headset fill:#7c3aed,stroke:#a78bfa,color:#fff
    classDef cortex fill:#1e3a5f,stroke:#60a5fa,color:#fff
    classDef backend fill:#14532d,stroke:#34d399,color:#fff
    classDef browser fill:#78350f,stroke:#fbbf24,color:#fff
    classDef temi fill:#831843,stroke:#f472b6,color:#fff
    classDef alias fill:#334155,stroke:#94a3b8,color:#94a3b8,stroke-dasharray:5 5

    class EPOC headset
    class CORTEX cortex
    class CFG,CLIENT,SERVER,MOOD,TEMICTRL backend
    class BROWSER browser
    class TEMI temi
    class ALIAS alias

    %% ===== Legend =====
    subgraph LEGEND ["Legend"]
        direction LR
        L1["raw EEG · BLE"]
        L2["JSON-RPC 2.0 · TLS"]
        L3["config dict"]
        L4["asyncio.Queue"]
        L5["WebSocket"]
    end
    classDef legend fill:#1e293b,stroke:#475569,color:#94a3b8
    class L1,L2,L3,L4,L5 legend
```

## Notes

- **Streams subscribed**: `met` (0.1 Hz), `pow` (8 Hz), `dev` (2 Hz), `eq` (2 Hz), `com` (8 Hz mental commands).
- **`com` mental commands** are trained in EMOTIV BCI — this code only displays them in the dashboard's Push / Pull / Neutral panel (for now this is limited, we will implement once we fine-tune and train BCI profile).
- **Temi speech is opt-in**: requires both `TEMI_ENABLED=1` and `TEMI_AUTO_SPEAK=1`, then a backend restart. Speech-only, rate-limited (60 s cooldown), deduped by mood.
- **`brainbot_main.py` is an alias** — running both it and `websocket_server.py` would spawn two acquisition processes competing for the same Cortex connection.
- **TLS certificate and hostname verification stay enabled**; if Python's trust store doesn't trust EMOTIV's root, set `CORTEX_CA_FILE` to the official `rootCA.pem` rather than disabling checks.
- **Scores are heuristics, not probabilities.** No emotion-accuracy claim is established.
- **No participant data is persisted**; `reset_assessment` clears the estimator's history between participants.