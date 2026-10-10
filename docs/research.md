# Cortex integration reference

This document describes the implemented integration. The subscription response, rather than a guessed channel or metric order, is authoritative.

## Connection

Cortex uses local WSS and JSON-RPC. This application accepts only loopback Cortex hosts. Its self-signed certificate can be trusted explicitly through `CORTEX_CA_CERT`; the default bypass is restricted to local Cortex.

Startup requests access, discovers an already-connected headset, authorizes the app, creates a session, then subscribes. Default sessions are opened without license activation. `CORTEX_ACTIVATE_SESSION=true` requests a one-session license debit and activates the session for licensed streams; this may consume quota. Authorization occurs after headset discovery so waiting for hardware does not repeatedly debit a license. Users approve app access in Launcher. Credentials and tokens remain on the Python side. RPC IDs distinguish replies from notifications on the shared socket.

- [Cortex API](https://emotiv.gitbook.io/cortex-api)
- [Session activation and licensing](https://emotiv.gitbook.io/cortex-api/session)
- [Authorization and debit](https://emotiv.gitbook.io/cortex-api/authentication/authorize)
- [Request access](https://emotiv.gitbook.io/cortex-api/authentication/requestaccess)
- [Data subscription](https://emotiv.gitbook.io/cortex-api/data-subscription)
- [Subscription result and columns](https://emotiv.gitbook.io/cortex-api/data-subscription/subscribe)
- [Sample formats and units](https://emotiv.gitbook.io/cortex-api/data-subscription/data-sample-object)
- [Mental command training](https://emotiv.gitbook.io/cortex-api/bci/training)

## Stream interpretation

| Stream | Actual data | Application behavior |
|---|---|---|
| `eeg` | Sensor amplitudes in µV plus metadata | Extract known sensor labels; plot unfiltered amplitudes, count interpolation flags |
| `pow` | `SENSOR/BAND` values in µV²/Hz | Display Cortex values, no locally invented bands |
| `met` | Metric values and `.isActive` flags | Display active finite values from 0–1; unavailable stays null |
| `com` | `act` string and `pow` from 0–1 | Display command/power, no automatic motion |
| `dev` | Battery, wireless signal, nested sensor contact quality | Flatten nested labels using their subscription schema |
| `eq` | Battery percentage, overall EEG quality, sample-rate quality, sensor quality | Display original labels/scales |
| `sys` | Training detection/event messages | Retain latest sample; this is not the signal-quality stream |
| `fac`, `mot` | Facial-expression or motion values | Optional subscription/transport support; no dedicated visualization yet |

An EPOC X commonly supplies AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, and AF4. The application reads labels from the subscription and displays only sensors actually present. Sampling depends on headset settings; no fixed receive rate is imposed by the application.

Metric schemas may contain active flags interleaved with values and vary by headset/version. Do not map a six-element list to guessed metric names. Null metrics can indicate poor EEG quality. Interest (`int`) and relaxation (`rel`) are separate metrics; attention is used only if the stream actually supplies it.

Cortex band definitions are theta 4–8 Hz, alpha 8–12 Hz, betaL 12–16 Hz, betaH 16–25 Hz, and gamma 25–45 Hz. These estimates use a two-second window. Delta is not supplied. No FFT-derived Delta or Gamma calculation is implemented locally.

Stream availability and rates depend on model, settings, and license. Raw EEG requires paid access. Partial subscription failures are reported without fabricating replacements. Consult the actual account/license and current vendor documentation before choosing streams.

## Boundaries

Physical headset pairing and electrode preparation are handled using Emotiv software/instructions. Participant mental-command training is available through the operator controls or EmotivBCI. The backend discovers an already-connected device; it does not pair hardware. Explicit profile controls use the single socket-owner request queue.

Every sample must match the active session, contain a finite timestamp, and match its schema. EEG samples with invalid amplitudes are rejected. Performance metrics with inactive or invalid values become unavailable. Short-lived sample history is for visualization, not clinical interpretation or lossless recording.
