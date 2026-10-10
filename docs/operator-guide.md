# Participant operation

Use one local operator and one headset. Open Operator view, check independent backend/Cortex/headset connections, then check the 14-channel diagram and separate `dev` contact and `eq` EEG quality. Missing credentials, denied streams, inactive metrics, stale measurements and poor quality are genuine unavailable states, not simulated substitutes.

1. **Start session** creates an application participant ID, clears participant history and keeps the existing Cortex session/socket. Recording and filtering are off.
2. **Collect baseline** while the participant rests voluntarily. The backend collects active `rel`, `eng`, `exc`, `str`, gated by fresh `dev`/`eq`. Progress reports valid counts and timestamp coverage. A timer cannot complete this step without samples. Fix the headset or subscriptions if progress stops.
3. **Begin assessment** after baseline is complete. Assessment uses its own bounded measurements. Long gaps restart coverage and interrupt persistence. Default met rates vary by license; use the observed rate to choose an appropriate count/duration. At the standard low met rate, the sample requirement can take longer than the configured duration; the application waits.
4. **Review estimate** and baseline-relative contributions. Unknown is a valid outcome. Suitable named estimates can be confirmed only while quality/metrics remain fresh.
5. **Confirm Temi expression** sends one operator-approved on-screen expression. It does not initiate navigation or movement. Follow the command history from accepted to completed/failed/cancelled/timed_out.
6. **End / reset** clears baseline, estimate, sample histories, filter state and command history; stops recording; attempts cancellation of accepted Temi commands; cancels training and unloads profiles owned by this application when Cortex is reachable. Save training before ending: unsaved changes are discarded on unload. Failed cleanup is an activity event; check robot/Launcher before the next participant. Profiles owned by another app are left alone. **Cancel session** performs the same cleanup.

A Cortex disconnect cancels an active participant and stops recording. After reconnect, start a new participant and baseline; no old estimate is reused. Browser reconnect alone preserves the backend participant. Participant resets never authorize, debit, activate or reopen Cortex. Existing explicitly configured active-session reconnect behavior can still consume license quota: keep `CORTEX_ACTIVATE_SESSION=false` unless your account and intended streams require activation.

## Configuration

All values are backend environment variables; restart after changes. Positive finite values are required.

| Variable | Default |
|---|---:|
| SESSION_BASELINE_SECONDS | 30 |
| SESSION_ASSESSMENT_SECONDS | 20 |
| SESSION_MINIMUM_SAMPLES | 10 |
| SESSION_FRESH_SECONDS | 15 |
| SESSION_SMOOTHING_SECONDS | 15 |
| SESSION_PERSISTENCE_SECONDS | 5 |
| SESSION_QUALITY_MINIMUM | 60 |

Freshness uses acquisition timestamps as well as transport arrivals. Quality requires contact `OVERALL` and EEG `overall` at least the configured threshold, and `sampleRateQuality >= 0.9`. Missing quality blocks assessment. Do not lower thresholds merely to produce an estimate.

## Profiles and training

Refresh profiles queries the current logged-in EMOTIV user's profiles and loaded profile through the single Cortex owner. Select an EPOC-compatible writable profile. Create profile makes a new empty profile name; it does not copy the loaded profile. Load is blocked until the current profile is explicitly unloaded. Another application's loaded profile cannot be changed. Cortex enforces model compatibility, read-only and ownership restrictions and reports errors to the operator.

Load the participant profile, train neutral, wait for `MC_Succeeded`, accept or reject, then train one chosen action. Accept/reject always applies to the pending action (including neutral), not the dropdown's later selection. Cancel training sends `reset`. `MC_Failed` requires cancellation/reset before retry. The backend validates actions/controls using `getDetectionInfo`; successful RPC acceptance is distinct from a `sys` training result. Save profile explicitly after accepting. This app does not automatically select a profile for another participant or save training.

Official references: [Cortex BCI workflow](https://emotiv.gitbook.io/cortex-api/bci), [profile ownership](https://emotiv.gitbook.io/cortex-api/bci/getcurrentprofile), [profile operations](https://emotiv.gitbook.io/cortex-api/bci/setupprofile), [training](https://emotiv.gitbook.io/cortex-api/bci/training).

## Dashboard

Raw EEG, vendor metrics and the application Estimated state have separate labelled panels. Waveforms support pause/resume, 2/5/10/30-second windows, automatic per-trace, common, and fixed 0–8000 µV scales. Pause freezes only drawing, not acquisition or recording. Memory is capped at 16,384 browser EEG samples, 256 backend EEG samples and 2,048 metric samples; an unusually high rate can shorten a selected window. Metric trends have 30/60/120/300-second selections, timestamp axes and gaps for null measurements or gaps over 15 seconds. Raw EEG traces break over gaps exceeding 100 ms. Sample age and observed rate appear in stream diagnostics.

Presentation view hides operator tools and technical diagnostics. Full screen uses the browser's accessible native mode; Escape exits. Toggle back to Operator view for controls. Reduced-motion preferences are respected. Activity uses real backend events; Clear activity clears the bounded event list without deleting recording markers already written.
