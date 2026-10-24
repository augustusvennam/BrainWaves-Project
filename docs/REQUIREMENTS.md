# BrainWaves build requirements and acceptance checklist

## Hardware

| Item | Requirement |
|---|---|
| Headset | One charged EMOTIV EPOC X with functioning sensors and references |
| Sensor preparation | Follow EPOC X instructions; prepare the supplied sensor pads with the specified saline solution |
| Wireless connection | Official EMOTIV wireless USB receiver preferred for the next test, or supported BLE |
| Computer | One supported laptop/desktop runs Launcher, Cortex, Python, and the dashboard |
| Recommended development capacity | 8 GB RAM and free disk space for Node/Python dependencies; project recommendation, not an EMOTIV minimum |
| Robot | Optional for the initial milestone: Temi with the team's Wizard-of-Oz app installed and running |
| Installation equipment | Android Studio/JDK and Android platform tools only if building/installing the Temi APK yourself |

A USB charging cable is not the wireless receiver. Cortex session creation does not
support headsets connected over the charging cable. Verify the headset is shown as
**connected**, not just discovered, before expecting samples.

## Operating system and software

- Recommended project target: Windows 11 x64. EMOTIV currently lists Windows 10 x64
  v1809+ / Windows 11 and macOS 12+ as supported desktop platforms. Check its current
  platform page before installing on a different machine.
- Install the current EMOTIV Launcher/Cortex service on the same computer as Python.
- EMOTIV's macOS guidance mentions Rosetta for Apple Silicon; check the current installer
  instructions for your specific Mac. Linux support is beta; use the team's supported
  desktop setup first.
- Project runtime recommendation: Python 3.11+ and Node.js 22 LTS with npm.
- Git to work on the branch; Python's venv and pip to isolate the backend.
- A browser with native WebSocket support.
- Python packages: websocket-client, websockets, PyYAML, python-dotenv; exact tested
  versions are in `requirements-lock.txt`.
- Frontend packages: React, TypeScript, Vite, Recharts, lucide-react and their lockfile
  dependencies, installed with `npm ci`.

No Rust toolchain, raw-EEG decoding library, separate cloud API, Vercel deployment,
database, or model download is required by this milestone.

## Account, licensing, and credentials

1. Sign in to Launcher with the account holding the Basic BCI entitlement.
2. Confirm a seat is available on this computer. The supplied support email states
   three machine-bound seats and that logging out does not free a seat; ask EMOTIV
   about moving an existing activation if necessary.
3. Use a registered Cortex application and its generated **client ID** and **client secret**.
   A friendly App ID alone does not replace those credentials.
4. Rotate the secret previously committed to this repository. Removing it from the
   current tree does not revoke it or remove Git history. Only the account owner
   can replace/revoke it in EMOTIV's account interface.
5. Put the replacement credentials in the ignored `.env`. Do not paste them into chat.
6. Accept the applicable EULA and approve app access in Launcher when requested.
7. Provide internet access for installation, sign-in, and initial authorization;
   do not assume a never-authorized machine can operate offline.

The current Basic build opens a session without Premium activation or session debit.
For EPOC X, raw `eeg` access needs the appropriate Developer API license; an EmotivPRO
software license is not proof of that entitlement. High-resolution `met` also has
separate scope/activation requirements. Those upgrades are unnecessary for this build.

## Streams used

| Stream | Documented rate | Meaning |
|---|---:|---|
| `met` | 0.1 Hz with Basic access | Performance metrics, roughly one packet per 10 seconds |
| `pow` | 8 Hz | Per-channel theta, alpha, low/high beta, gamma band powers |
| `dev` | 2 Hz | Battery, wireless signal and sensor contact quality |
| `eq` | 2 Hz | EEG quality and sample-rate quality |

Band powers are derived values, calculated from two seconds of EEG according to the
Cortex documentation. Eight updates per second do not mean eight independent windows.
They cannot reconstruct a raw EEG waveform. The dashboard shows channel-mean band power.
The estimator uses only active valid performance metrics; it does not derive emotion
from a band ratio or train a machine learning model.

## Ports, network, and certificates

| Connection | Address | Requirement |
|---|---|---|
| Python → Cortex | `wss://localhost:6868` | Cortex running locally; TLS certificate trusted |
| Browser → Python | `ws://127.0.0.1:8080` | Backend running on the same computer |
| Browser → Vite | `http://127.0.0.1:3000` | Frontend dev server running |
| Python → Temi | `ws://<TEMI_IP>:8175` | Same reachable LAN; Android app listening |

- Keep the initial dashboard on localhost. Other-computer access needs intentional
  changes to server binding, browser origin allowlist, and frontend WebSocket URL.
- Campus/guest Wi-Fi may isolate clients. Confirm the laptop can reach the robot's
  port; same Wi-Fi name alone does not establish reachability.
- Allow the relevant local applications through any firewall blocking these connections.
- Cortex requires secure WebSockets. The client keeps certificate/hostname verification
  enabled. If Python's trust store does not trust the EMOTIV root, obtain the official
  certificate below and set `CORTEX_CA_FILE` to its absolute local path. Do not disable TLS checks.
- Avoid an HTTPS-hosted dashboard pointing at a plain `ws://` local backend; this
  build is deliberately served over local HTTP.

## Assessment behavior and adjustable defaults

`config/settings.yaml` contains demonstration thresholds, not clinically or
experimentally validated settings:

- A 60-second rolling history; at least 3 valid samples spanning 20 seconds.
- EEG quality at least 70 and sample-rate quality at least 0.9, refreshed within 5 seconds.
- Metrics considered stale after 25 seconds.
- Required active metrics: engagement, excitement, stress, relaxation.
- Winning averaged score at least 0.55 and at least 0.08 above the next score.
- Two consecutive qualifying decisions before displaying a stable estimate.

With approximately 10-second metric spacing, expect the first possible stable estimate
around 30 seconds after the first valid sample; quality, missing metrics, and ambiguous
scores can extend that or prevent an estimate. There is no guaranteed output deadline.
Labels are Engaged, Excited, Stressed, and Relaxed. A stable result is an estimated
state, not a verified emotion. Focus/attention, when available, is read from its
reported metric rather than invented from engagement.

Use the new-assessment button between participants. No automated baseline recording,
training, mood-accuracy study, or persistent data export is implemented in this milestone.
To evaluate accuracy later, define labels and collect participant self-reports with
appropriate consent, then evaluate separately from connectivity and rendering.

## Temi protocol and limitations

The linked `TemiWebsocketServer.java` requires `id` for `speak`. The linked
`RobotApi.onTtsStatusChanged` broadcasts **JSON containing that ID** on completion.
The repository's older prose describing `TTS_COMPLETED/...` does not match this code.
This build follows the Java implementation, not that older example.

The client waits for the matching ID and ignores other clients' completion messages.
The Android implementation stores a single `speak_id`, so concurrent speech from
other tools/operators can interfere with acknowledgement. Use one speech controller
for the demonstration. Automatic speech is disabled by default and rate-limited;
this milestone does not add face/animation rendering to the Android app.

## Acceptance checks on your computer

- [ ] Rotate the exposed secret, fill `.env`, and verify the account's seat/entitlement.
- [ ] Launcher shows the physical EPOC X connected with usable sensor quality.
- [ ] `python -m scripts.test_cortex --seconds 45` receives all four actual streams.
- [ ] Dashboard shows fresh metric timestamps, band data, battery, and quality.
- [ ] After enough valid samples, the estimator either produces a stable state or
      explains why data/score separation is insufficient.
- [ ] Removing headset contact invalidates the estimate; loss of Cortex clears it
      and the backend attempts reconnection.
- [ ] Starting a new assessment clears the previous participant's estimator history.
- [ ] Optional: `python -m scripts.test_temi` receives the greeting and matching speech completion.
- [ ] Optional: enable auto speech, then confirm one stable estimate is spoken.

## Verification in the build environment

Automated verification covers protocol parsing, response errors, partial subscription
failure, approval polling, column-metadata ordering, single socket ownership, invalid
metrics, quality/staleness reset, Temi completion IDs, and normalized data delivered
over a real local WebSocket. The frontend production build is also checked.

The build environment has no physical EPOC X, signed-in EMOTIV Launcher, or Temi.
Therefore hardware, license activation, real Bluetooth/receiver connectivity, device
packet rates, speech, and mood accuracy remain **unverified** until the above local checks.

## Primary references

- [EMOTIV Cortex platform requirements](https://emotiv.gitbook.io/system-requirements/cortex-api)
- [Cortex setup and access levels](https://emotiv.gitbook.io/cortex-api)
- [Connection and official root CA guidance](https://emotiv.gitbook.io/cortex-api/connecting-to-the-cortex-api)
- [Official EMOTIV rootCA.pem](https://github.com/Emotiv/cortex-v2-example/blob/master/certificates/rootCA.pem)
- [API lifecycle](https://emotiv.gitbook.io/cortex-api/overview-of-api-flow)
- [Authorization and debit parameters](https://emotiv.gitbook.io/cortex-api/authentication/authorize)
- [Session creation](https://emotiv.gitbook.io/cortex-api/session/createsession)
- [Streams and rates](https://emotiv.gitbook.io/cortex-api/data-subscription)
- [Column metadata and sample interpretation](https://emotiv.gitbook.io/cortex-api/data-subscription/data-sample-object)
- [Team's Temi Android source](https://github.com/augustusvennam/temi-woz-android)
