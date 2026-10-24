# BrainWaves — Cortex Basic integration

Local EPOC X demonstration: EMOTIV Cortex → one Python backend → React dashboard,
with optional estimated-state speech through the Temi Wizard-of-Oz Android app.

This build uses **Basic BCI streams** (`met`, `pow`, `dev`, `eq`). It does not need
raw EEG access, `emotiv-rs`, mental-command training, a database, or cloud hosting.

## Requirements

See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for the full hardware, accounts,
software, networking, acceptance checks, and known limitations.

- A charged EPOC X, prepared sensors, and official wireless receiver or supported BLE.
- Windows 10/11 x64 recommended, or a supported macOS installation.
- EMOTIV Launcher with Cortex running, signed into the licensed account.
- Registered Cortex client ID and a **newly rotated** client secret; app approval in Launcher.
- Python **3.11+**, Node.js **22 LTS**, npm, and Git (project recommendations).
- Optional Temi robot with the linked Android app running on the same LAN.

## Install — Windows PowerShell

From this project's root directory:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
npm ci
Copy-Item .env.example .env
```

Edit `.env` locally. Set `EMOTIV_CLIENT_ID` and `EMOTIV_CLIENT_SECRET`. Leave Temi
disabled for the first Cortex test. Never put the secret in browser code or commit `.env`.
If Python cannot trust Cortex's TLS certificate, set `CORTEX_CA_FILE` to the absolute
path of EMOTIV's official `rootCA.pem` (link in the requirements document).
Certificate checking stays enabled.

## Install — macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
npm ci
cp .env.example .env
```

Use Python 3.11+; edit `.env` as above. On macOS substitute `.venv/bin/python` for
`.\.venv\Scripts\python.exe` in the following commands.

## Verify the physical headset first

1. Open Launcher and sign in. Confirm the physical headset is connected.
2. Prepare the sensors according to the headset instructions; check quality in EMOTIV software.
3. Run the following test and approve the app in Launcher if prompted:

```powershell
.\.venv\Scripts\python.exe -m scripts.test_cortex --seconds 45
```

The test requires actual decoded packets from **all four streams**. It prints
column metadata and packet counts, without credentials. A connection or a successful
subscription alone does not constitute a pass. This smoke test does not validate mood accuracy.

## Run — two terminals

Terminal 1, from project root:

```powershell
.\.venv\Scripts\python.exe -m src.websocket_server
```

Terminal 2:

```powershell
npm run dev
```

Open **http://127.0.0.1:3000**. Backend: `ws://127.0.0.1:8080`.
Do not also run `brainbot_main.py`: it is an alias for the same backend.
Use module commands (`python -m ...`), not `python src/file.py`.

The dashboard remains accessible while Cortex is unavailable and reports its actual
status. The backend retries after disconnection. Backend connectivity, headset data,
and usable EEG quality are shown separately.

## Optional Temi speech

Install and launch the team's [Temi Android app](https://github.com/augustusvennam/temi-woz-android).
Set `TEMI_IP` to its LAN address. Run the explicit speech-only hardware test:

```powershell
.\.venv\Scripts\python.exe -m scripts.test_temi
```

This sends one spoken sentence and waits for the app's JSON completion containing
the matching command `id`. To enable automatic speech, set both `TEMI_ENABLED=1`
and `TEMI_AUTO_SPEAK=1`, then restart the backend. Stable new estimates are spoken
at most once a minute. Speech requests never run on the Cortex socket reader.
No navigation or robot movement is triggered by this build.

Use **Start a new assessment** between participants; it clears the estimator's
history. The implementation does not persist participant data.

## Development checks

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
npm run build
```

Unit/integration tests use protocol fixtures; they do not substitute for live hardware
verification. `requirements-lock.txt` records the Python versions exercised by this build;
`package-lock.json` supplies the frontend dependency lock.

## Code map

- `src/cortex_api_client.py`: trusted TLS, JSON-RPC, approval, discovery, session,
  subscription metadata, and a single socket reader.
- `src/websocket_server.py`: acquisition lifecycle, normalized browser events,
  fresh-data checks, reconnection, and optional Temi speech.
- `src/mood_determiner.py`: quality checks, valid-sample window, state stability.
- `src/temi_controller.py`: matching command IDs and actual speech completion.
- `src/services/websocket.ts`: browser transport and reconnect cleanup.
- `tests/test_integration.py`: protocol, estimation, and real local WebSocket tests.

The state estimator is a demonstration heuristic. Its scores are **not probabilities**,
and no emotion-accuracy claim is established by a successful build or smoke test.
