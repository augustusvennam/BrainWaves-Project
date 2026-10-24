# First Cortex Basic integration build

Base repository commit: `57d380dc68d6991892be8163333f35883afd7277`.
Working branch: `build/cortex-basic-integration` (local; not pushed).

Implemented:

- One Cortex acquisition owner, JSON-RPC request routing, Launcher approval polling,
  headset discovery/connection, Basic session and subscriptions.
- Metadata-based decoding, including nested device sensor columns; partial subscription
  failures and RPC errors are no longer reported as successful subscriptions.
- Environment credentials, trusted TLS, and removal of credentials from current config.
- Reconnection and explicit offline state; no fabricated readings.
- Quality/freshness checks, windowed stable estimates, per-participant assessment reset.
- React charts for active metrics and frequency-band power with unavailable states.
- Optional speech-only Temi integration using matching JSON completion IDs.
- Windows/macOS run instructions and complete requirements/acceptance checklist.

Verification:

- 11 automated tests passed using Python 3.12; tests include a real local WebSocket.
- TypeScript checking and Vite production build passed.
- Backend subprocess accepted an allowed browser-origin connection with no credentials;
  it correctly reported Cortex unavailable and the estimate as insufficient data.
- Git whitespace check passed.
- Visual browser verification was unavailable: Chromium was not installed and its
  download failed in this environment. No rendered-browser QA is claimed.
- Physical headset, Launcher licensing, receiver/BLE, Temi speech, and mood accuracy
  remain unverified here. Run the hardware checks in REQUIREMENTS.md on your computer.

The downloadable source archive excludes Git history, local environments, installed
dependencies, and credentials. No remote branch or pull request has been published.
