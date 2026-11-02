# Demo Setup — Temi Hotspot

The laptop and the Temi connect through the phone's hotspot. There is no
router, so the laptop's LAN IP is the address the Temi reaches.

## 1. Open the firewall for the demo ports

Hotspot networks are treated as **public** by Windows, which blocks inbound
connections by default. Run PowerShell **as Administrator**:

```powershell
New-NetFirewallRule -DisplayName "BrainWaves HTTP (3000)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000 `
  -Profile Any
New-NetFirewallRule -DisplayName "BrainWaves WebSocket (8080)" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 `
  -Profile Any
```

`-Profile Any` covers Domain, Private, and Public — the hotspot shows up as
public, which is why the default (Domain + Private) rule would not apply.

## 2. Start the services

**Terminal 1 — backend** (from the project root):

```powershell
.\.venv\Scripts\python.exe -m src.websocket_server
```

It prints the Temi URL on startup, e.g.:

```
INFO Dashboard backend: ws://0.0.0.0:8080
INFO Open on Temi: http://192.168.45.12:3000
INFO Robot face:    http://192.168.45.12:3000/face
```

**Terminal 2 — frontend (development)**:

```powershell
npm run dev
```

Or, for the production bundle the demo uses:

```powershell
npm run demo:build
npm run demo:serve
```

## 3. Pre-event test — prove the Temi can reach the laptop

Before the demo, open this on a **phone connected to the same hotspot**:

```
http://<laptop-ip>:3000
```

- If you see the Operator Dashboard, the network path works.
- If you see a blank page or "connection refused", the firewall rule is missing
  or the laptop's IP changed. Re-run step 1 and check `ipconfig`.

## 4. On the Temi

In the WOZ app, send an `openURL` command:

```
http://<laptop-ip>:3000/face
```

The robot's browser loads the face page and connects back to the laptop's
backend. As you think push / pull / neutral, the face, title, and background
update in real time.

## 5. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Temi shows a blank page | Firewall rule missing, or laptop IP changed |
| Temi shows the page but face never updates | Backend not reachable from the Temi (check `ws://` connection) |
| Hotspot drops mid-demo | The frontend reconnects automatically; the page shows "Reconnecting…" until it returns |