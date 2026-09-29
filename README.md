# BrainWaves Project

**Brain–Robot Interaction Demo: "BrainBot: Can you control a robot with your brain?"**

A mood-determining and brain-controlled robotics project using the Emotiv EPOC X EEG headset and the Temi robot.

---

## Project Architecture

```
EMOTIV EPOC X (EEG Headset)
    │
    ▼
Emotiv Cortex API (WebSocket)
    │
    ▼
Python Controller (cortex_api_client.py)
    │
    ├── Mood Analysis (mood_determiner.py)
    └── Command Translation (brainbot_main.py)
            │
            ▼
Temi Robot SDK (HTTP/WebSocket)
            │
            ▼
Temi Robot → Actions (Move Forward, Turn, Dance)
```

---

## Project Structure

```
BrainWaves Project/
├── README.md
├── docs/
│   ├── research.md          # Emotiv + Cortex API + Temi research notes
│   ├── architecture.md      # System architecture & data flow
│   └── api_reference.md     # Cortex API quick reference
├── src/
│   ├── cortex_api_client.py # Cortex API WebSocket wrapper
│   ├── mood_determiner.py   # EEG signal processing & mood classification
│   ├── temi_controller.py   # Temi robot communication layer
│   ├── brainbot_main.py     # Main integration & interaction flow
│   └── config.py            # Configuration loader
├── scripts/
│   ├── setup.sh             # Environment setup
│   ├── test_cortex.py       # Cortex API connectivity test
│   └── test_temi.py         # Temi robot connectivity test
├── config/
│   └── settings.yaml        # Project configuration
└── requirements.txt         # Python dependencies
```

---

## Status

- [x] Project structure created
- [x] Cortex API research completed
- [x] Temi integration research completed
- [x] Base framework & code architecture ready
- [ ] Cortex API credentials (pending device registration)
- [ ] Temi robot SDK access (pending)
- [ ] Hardware testing (pending device availability)

---

## Getting Started

```bash
cd "BrainWaves Project"
bash scripts/setup.sh
python src/brainbot_main.py
```
