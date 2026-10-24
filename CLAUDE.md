# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

**BrainWaves** — Local EPOC X demonstration: EMOTIV Cortex → one Python backend → React dashboard, with optional estimated-state speech through the Temi Wizard-of-Oz Android app.

This build uses **Basic BCI streams** (`met`, `pow`, `dev`, `eq`). It does not need raw EEG access, `emotiv-rs`, mental-command training, a database, or cloud hosting.

## Architecture

- **Cortex API** (`src/cortex_api_client.py`): single JSON-RPC WebSocket client over `wss://localhost:6868`. One socket reader owns the connection; callbacks never call RPC directly. Handles trusted TLS, request/response routing, approval polling, headset discovery/connection, session creation, subscription metadata, and metadata-based stream decoding (including nested device sensor columns).
- **Backend** (`src/websocket_server.py`): `EEGWebSocketServer` — acquisition lifecycle, normalized browser events, fresh-data checks, reconnection, and optional Temi speech. Runs on `ws://127.0.0.1:8080`.
- **Estimator** (`src/mood_determiner.py`): quality checks, valid-sample window, state stability. Scores are a demonstration heuristic, **not probabilities**.
- **Temi** (`src/temi_controller.py`): speech-only client for the linked Temi Android app (`ws://<TEMI_IP>:8175`). Matches JSON completion IDs; sending is not completion.
- **Frontend** (`src/`, Vite + React 18 + TypeScript): dashboard at `http://127.0.0.1:3000`. `src/App.tsx` composes sections directly. `src/components/ui/` is the component library. `src/services/websocket.ts` is the browser transport with reconnect cleanup. `src/EEGDashboard.tsx` is the live-data panel.
- **Config** (`src/config.py`): loads `config/settings.yaml` (non-secret defaults) plus `.env` credentials. `src/brainbot_main.py` is an alias for the same backend — do not run both.

## Commands

### Backend (Python)
```bash
# Create venv and install pinned deps (Python 3.11+)
python -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt

# Copy .env.example to .env and fill in EMOTIV_CLIENT_ID / EMOTIV_CLIENT_SECRET
cp .env.example .env

# Real hardware smoke test — requires a connected EPOC X in Launcher
python -m scripts.test_cortex --seconds 45

# Run the backend (Terminal 1)
python -m src.websocket_server

# Optional Temi speech test
python -m scripts.test_temi
```

### Frontend (Node 22 LTS)
```bash
npm ci              # install from lockfile
npm run dev         # Vite dev server on http://127.0.0.1:3000
npm run build       # production build to dist/ (tsc + vite)
```

### Tests
```bash
python -m unittest discover -s tests -v   # 11 tests: protocol, estimation, real local WebSocket
```

## Key Details

- **Credentials**: `EMOTIV_CLIENT_ID` and `EMOTIV_CLIENT_SECRET` live in the ignored `.env` file (copied from `.env.example`). Never commit or paste them. Rotate any previously committed secret — removing it from the tree does not revoke it.
- **TLS**: certificate/hostname verification stays enabled. If Python's trust store does not trust EMOTIV's root, set `CORTEX_CA_FILE` to the official `rootCA.pem` path. Do not disable TLS checks.
- **Streams**: `met` (0.1 Hz), `pow` (8 Hz), `dev` (2 Hz), `eq` (2 Hz). Band powers are derived values, not raw EEG.
- **Headset selection**: the client never silently selects a virtual device. Set `CORTEX_HEADSET_ID` explicitly if multiple headsets exist. A USB charging cable is not the wireless receiver.
- **Reconnection**: the backend retries after disconnection and reports its actual status. The dashboard remains accessible while Cortex is unavailable.
- **Temi**: disabled by default. Set `TEMI_ENABLED=1` and `TEMI_AUTO_SPEAK=1`, then restart the backend. Speech never runs on the Cortex socket reader.
- **Assessment**: use "Start a new assessment" between participants to clear the estimator's history. No participant data is persisted.

## Verification

- 11 automated tests pass (protocol fixtures, estimation, real local WebSocket).
- TypeScript check and Vite production build pass.
- Physical headset, Launcher licensing, receiver/BLE connectivity, Temi speech, and mood accuracy remain unverified until the hardware checks in `docs/REQUIREMENTS.md` are run on a machine with an EPOC X.

## Notes

- The state estimator is a demonstration heuristic. Its scores are not probabilities, and no emotion-accuracy claim is established by a successful build or smoke test.
- The frontend is served over local HTTP, not HTTPS, to avoid mixed-content issues with the plain `ws://` backend.