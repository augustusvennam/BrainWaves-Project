# Verification and hardware acceptance

Local verification on October 10, 2026, on macOS with Node 25.9.0 and Python 3.14.4. No headset, Cortex credentials/license, Temi robot, Android SDK or Gradle was available for hardware/Android acceptance.

## Automated checks

Before changes: 7 Vitest tests and 25 unittest tests passed; TypeScript, ESLint/Ruff and production build passed. The repository uses unittest, not pytest.

After changes: 11 frontend tests and 42 backend tests passed, including optional SciPy filtering. TypeScript, ESLint/Ruff, production Vite build, dependency consistency (`pip check`) and `git diff --check` passed. Tests cover schema parsing, inactive/null values, sample sequence cursors, slow consumers, duplicate/out-of-order timestamps, recording before browser eviction, raw markers/loss estimates, malformed replay, replay isolation/EOF, reconnect/reset, baseline/assessment sample coverage, persistence, stale-review masking, invalid transitions, profile ownership, queue ownership/epoch cancellation, neutral-action acceptance, and command acknowledgements/completion/timeouts. Controlled fixtures exist only in tests.

`constraints.txt` pins the verified runtime/dev transitive versions; `requirements-filter.txt` pins SciPy/NumPy. GitHub Actions is configured for Python 3.11/3.14 and Node 24. That hosted workflow has not been run or published in this session. The local environment is Python 3.14; other OS/Python installations remain CI/setup acceptance checks.

## Browser verification

`npm run dev` starts both local services. Headless Chrome checked the actual backend connection, unavailable/empty hardware states, real start/baseline/end routes and sample gating without hardware. Browser-only intercepted protocol fixtures checked review/confirmation transitions, waveforms, pause/resume, windows/common scaling/all channels, timestamped trends, invalid snapshot recovery, socket disconnect/reconnect, history resets and Replay command isolation. Desktop 1440×1000 and phone 390×844 had no horizontal overflow or uncaught page errors. These fixtures do not demonstrate physical acquisition, training or robot completion.

Repeat with services running: install Python Playwright in a development environment, install its Chrome-compatible browser, then `python scripts/browser_check.py`. The script uses the installed Google Chrome channel and writes ignored screenshots under `artifacts/`. It starts no hardware mock service. Screenshot content labelled Controlled browser test fixture is test-only. The design detector reported only the pre-existing status accent border, retained to preserve the user's requested visual style.

## Hardware acceptance procedure (not performed)

1. Record operating system, Cortex/Launcher, headset firmware, account/license, and Android/Temi Launcher/SDK versions. Configure real credentials locally and approve access. Keep credentials out of browser variables.
2. Prepare and fit EPOC X under vendor instructions. Verify 14 channel labels, contact/EEG quality, active metrics, raw amplitude units and the actual reported `settings.eegRate`. Confirm denied streams are clearly unavailable, not replaced.
3. Complete a real baseline and assessment at the actual met rate. Interrupt quality/freshness and confirm no time-only success; compare raw timestamps against another trusted acquisition display. End/reset and verify the Cortex session ID stays unchanged and no authorization/debit/createSession occurs on participant reset.
4. Load an EPOC-compatible writable owned profile, train neutral then one action, exercise accept/reject/cancel, save and reload. Try another app's profile and verify this app refuses to alter it. Verify `sys` event timing on the real Cortex version.
5. Power off/reconnect the headset; ensure participant cancellation, fresh empty histories and new baseline. Explicit active Cortex reconnects can consume quota; verify account behavior before using activation in repeated demos.
6. With consent, record a sustained real session without browser clients; compare counts/timestamps/markers against acquisition metadata, deliberately delay a browser consumer, inspect summary loss and quality flags, and verify raw data survives browser eviction. Test storage-full/size-limit behavior. Replay the actual file, including EOF, and verify no robot/profile actions occur.
7. Compare causal filtered and raw views using acquisition rate metadata. Check rate-change/discontinuity resets and frequency-dependent delay; document artifacts and limitations. No filter accuracy or emotion accuracy is claimed.
8. Build/install `android-bridge` with the documented toolchain. On the real robot verify readiness, authentication, exact command IDs, speech/TTS completion, display expression, duplicate-ID idempotency, stop/cancel, timeout and network loss. Verify physical stopping using vendor procedures, independently of the HTTP/SDK acknowledgement.
9. Follow [voluntary participant self-report evaluation](estimated-state.md) before reporting any estimated-state performance. Record abstentions, excluded intervals and all measured results.

There is no autonomous navigation, dancing, EEG-triggered motion, validated emotion recognition, or verified emergency-stop system. Lab Streaming Layer remains an optional future architecture extension.
