
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this repository.

## Project Overview

**BrainWaves Project** — Brain-robot interaction demo: "BrainBot: Can you control a robot with your brain?"

Architecture: **EMOTIV EPOC X (EEG Headset) → Emotiv Cortex API (wss://localhost:6868) → Python Controller → Temi Robot SDK → Robot Actions**

The project has two halves:
- **Frontend** (React 18 + Vite + TypeScript): A monitoring dashboard at `src/` that visualizes Cortex data streams (`com`, `met`, `sys`). Built with Linear design system tokens (`src/styles/tokens.css`) and a component library in `src/components/ui/`. Deployed to Vercel (project ID: `prj_DcHiYDCplOdAQY10DcI3v3fVGSaC`, org: `team_UtnjFTxkFQM14O7yUnacmp4p`).
- **Backend** (Python): `src/brainbot_main.py` is the main integration. It connects to Cortex via `cortex_api_client.py`, processes EEG via `mood_determiner.py`, and controls Temi via `temi_controller.py`. Config loaded from `config/settings.yaml`.

## Commands

### Frontend (Vite)
```bash
npm run dev      # Start dev server on port 3000
npm run build    # Build to dist/ (used by Vercel)
npm run preview  # Preview built output on port 4173
```

### Backend (Python)
```bash
python src/brainbot_main.py        # Run the full BrainBot application
python scripts/test_cortex.py      # Test Cortex API connectivity
python scripts/test_temi.py        # Test Temi robot connectivity
```

### Vercel Deployment
The project is already linked to Vercel (`project.json` in `.vercel/`). Vercel config is at `vercel.json` (build: `npm run build`, output: `dist`). The Vercel CLI is not installed — use the Vercel web dashboard at `https://vercel.com` or install `@vercel/cli` to deploy from CLI.

## Key Architecture

### Data Flow
Cortex streams three data types to the Python backend:
- `com` — mental commands (action + power, e.g. `["push", 0.7]`)
- `met` — performance metrics (eng, exc, str, rel, int, lex) → mood classification
- `sys` — system events (connection quality, battery)

The frontend dashboard is currently **static** (mock data in `App.tsx`) but is structured to be WebSocket-ready. The `App.tsx` component holds `monitors`, `milestones`, and `logs` state with clear prop-passing interfaces.

### Frontend Structure
- `src/main.jsx` — React entry point
- `src/App.tsx` — Main dashboard composition (Header, ProjectProgress, SystemStatus, ActivityLog, Architecture)
- `src/styles/tokens.css` — Linear design tokens (dark-mode-first, `--surface-canvas: #010102`, accent `#5e6ad2`, 4-step surface ladder, hairline borders)
- `src/components/ui/` — Barrel-exported component library:
  - `Button.tsx`, `Badge.tsx`, `Card.tsx` (Card/CardHeader/CardBody)
  - `Monitor.tsx` — System status monitor with live state
  - `LogEntry.tsx` — Timestamped, color-coded log entries (info/warn/error)
  - `MilestoneCard.tsx` — Milestone card with status transitions
  - `ArchitectureDiagram.tsx` — Horizontal flow: EPOC X → Cortex → Python → Temi
  - `SectionTitle.tsx`, `SectionSubtitle.tsx` — Section labels
  - `DashboardSections.tsx` — Composite section renderer (not currently used by App.tsx)
- `src/components/` — Legacy `.jsx` files (Header, ProjectProgress, SystemStatus, ActivityLog, Architecture) — these are the pre-redesign versions. The new implementation lives in `App.tsx` + `src/components/ui/`.

### Backend Structure
- `src/brainbot_main.py` — `BrainBot` class: connects to Cortex, subscribes to streams, classifies mood, determines robot action, executes on Temi
- `src/cortex_api_client.py` — WebSocket wrapper for Emotiv Cortex API
- `src/mood_determiner.py` — EEG signal processing and mood classification
- `src/temi_controller.py` — Temi robot communication (HTTP/WebSocket)
- `src/config.py` — Loads `config/settings.yaml`
- `src/mock-api.js` — Mock API for frontend development

### Configuration
- `config/settings.yaml` — Contains Emotiv credentials, EEG parameters, mood thresholds, Temi settings, interaction config
- `vercel.json` — Vercel build config (buildCommand, outputDirectory, routes)
- `vite.config.ts` — Vite config with React plugin, build output to `dist/`, sourcemaps, manual chunks for vendor/ui bundles

## Design System
- **Linear-inspired**: dark-mode-first, Inter + JetBrains Mono, indigo accent `#5e6ad2`, semi-transparent borders, 4-step surface ladder (`#010102` → `#0f1011` → `#141516` → `#18191a` → `#191a1b`)
- **Tokens**: `src/styles/tokens.css` defines all CSS variables (colors, spacing, radii, typography, z-index, motion)
- **Motion**: GSAP-ready, medium intensity, `prefers-reduced-motion` respected
- **Breakpoints**: 640/768/1024/1280 (mobile-first)
- **Icons**: lucide-react (already in package.json)
- **Fonts**: Google Fonts Inter (cv01, ss03) + JetBrains Mono

## Notes
- The frontend is currently static with mock data. Real-time data readiness is built into the component interfaces — `monitors`, `milestones`, and `logs` are all prop-driven with clear TypeScript interfaces.
- The `src/components/ui/DashboardSections.tsx` file is a composite renderer that is not currently imported by `App.tsx`. `App.tsx` composes sections directly. Either file can be used as the composition entry point.
- The old `.jsx` files in `src/components/` are pre-redesign and should be removed once the new implementation is verified.
- Python backend requires `websocket-client`, `pyyaml`, `numpy`, `scipy`, `requests` (see `requirements.txt`).
- Emotiv credentials are in `config/settings.yaml` — do not commit changes to this file if credentials are real.