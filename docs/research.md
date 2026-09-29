# BrainWaves Project — Research & Technical Background

## 1. Emotiv EPOC X & Cortex API Overview

### Hardware Highlights
- **Channels:** 14 EEG channels (AF3, F7, F3, FC5, T7, P7, O1, O2, P8, T8, FC6, F4, F8, AF4) + 2 references (CMS/DRL)
- **Sampling Rate:** 128 Hz or 256 Hz
- **Sensors:** Saline-soaked felt pads (rehydrated with distilled water)
- **Connectivity:** Bluetooth 5.0 or 2.4 GHz USB Dongle
- **Motion Sensors:** 9-axis IMU (gyroscope, accelerometer, magnetometer)

### Software & API Access
- **Emotiv Launcher:** Central app required to manage device connection and user profile login.
- **Cortex API (v2/v4):** WebSocket + JSON-RPC 2.0 interface running locally at `wss://localhost:6868` or remote `wss://emotiv.com:9000`.
- **Authentication Flow:**
  1. `getCortexInfo` → Verify Cortex service is running
  2. `requestAccess` → User grants permission in Launcher UI
  3. `authorize` → Exchange Client ID/Secret for auth token
  4. `queryHeadsets` → Find connected EPOC X
  5. `createSession` → Start active session with headset
  6. `subscribe` → Streams: `eeg`, `mot` (motion), `com` (mental commands), `fac` (facial expressions), `met` (performance metrics / mood)

### Mental Commands (`com` stream)
- Supported commands: `neutral`, `push`, `pull`, `lift`, `drop`, `left`, `right`, `rotate_clockwise`, `rotate_counter_clockwise`, `rotate_forwards`, `rotate_backwards`, `disappear`
- Requires calibration via Launcher or Cortex API (`training` method)

### Mood / Performance Metrics (`met` stream)
- Metrics provided at 0.1 Hz (basic) or 2 Hz (premium):
  - `eng` (Engagement)
  - `exc` (Excitement)
  - `str` (Stress)
  - `rel` (Relaxation / Interest)
  - `foc` (Focus / Attention)

---

## 2. Temi Robot SDK & API Integration

### Communication Protocol
- Temi runs Android with the **temi Android SDK**.
- For external control from Python/Node.js, we use a lightweight **HTTP/WebSocket gateway server** running on Temi or an intermediary bridge.

### Supported Actions
- `move_forward(distance_m)`
- `turn_left(angle_deg)` / `turn_right(angle_deg)`
- `speak(text)`
- `dance()` (predefined movement sequence)
- `go_to(location_name)`

---

## 3. Demo Flow: "BrainBot: Can you control a robot with your brain?"

1. **Introduction / Calibration (60 seconds)**
   - Visitor puts on EPOC X.
   - App checks signal quality across all 14 channels.
   - Visitor completes a 10-second baseline focus / mental command training (`push` or `focus`).

2. **Mood Assessment (15 seconds)**
   - App reads real-time performance metrics (`met` stream).
   - Classifies mood: *Focused*, *Relaxed*, *Excited*, or *Stressed*.
   - Temi speaks: *"Welcome! I detect you are feeling [Mood] right now."*

3. **Mental Command Control (30 seconds)**
   - Visitor thinks `PUSH` or concentrates deeply.
   - Real-time power/command meter fills up on the display.
   - Once threshold (> 0.6) is crossed, command triggers Temi.

4. **Robot Action Execution**
   - **Low Focus / Neutral:** Temi turns left and right, asking for more concentration.
   - **Medium Focus:** Temi moves forward 1 meter.
   - **High Focus / Strong Push:** Temi performs a short victory dance!

5. **Reset & Next Visitor**
