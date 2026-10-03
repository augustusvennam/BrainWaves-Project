# Repository guidance

BrainWaves is a local Emotiv Cortex monitor with a Python FastAPI backend and React/TypeScript frontend.

Read README.md for setup, docs/research.md for stream formats, and docs/temi-bridge.md for the optional robot bridge.

- Start both services: `npm run dev`.
- Frontend only: `npm run dev:frontend`; backend only: `npm run dev:backend`.
- Checks: `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`.
- Runtime settings are in `.env`; `.env.example` lists supported variables. Never expose Emotiv credentials through `VITE_` variables.
- Cortex socket reads belong to one owner in backend/services/cortex.py. Match RPC IDs and interpret sample arrays using returned subscription columns.
- Preserve unavailable/inactive metrics. Never introduce generated EEG values into runtime code.
- Keep state, sample history, and network queues bounded. Clear old participant data on session changes.
- The dashboard displays mental commands; it does not automatically move Temi.
- Physical headset/robot behavior cannot be claimed tested using protocol fixtures alone.
- Prefer small, explicit modules and comments explaining non-obvious protocol behavior.
