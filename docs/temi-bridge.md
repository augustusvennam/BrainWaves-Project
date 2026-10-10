# Temi Android bridge contract v1

Temi does not expose these custom HTTP endpoints natively. `android-bridge/` provides the Android source using official `com.robotemi:sdk:1.138.0` and NanoHTTPD 2.3.1. Backend credentials stay out of the dashboard bundle. Keep this bridge on a trusted local LAN; HTTP bearer transport is not encrypted. Do not expose it to the internet.

Set `TEMI_BRIDGE_URL=http://<robot-LAN-IP>:8080/api` and the same `TEMI_BRIDGE_TOKEN` entered on the robot (minimum 16 characters). Restart backend. Every bridge request uses `Authorization: Bearer <token>`.

| Method/path relative to `/api` | Body/result |
|---|---|
| GET `/status` | `{ "robot_connected": true, "contract_version": 1 }`; boolean comes from `OnRobotReadyListener` |
| POST `/commands` | `{ "id": "UUID", "action": "speak", "payload": { "text": "Hello" } }` |
| POST `/commands` | `{ "id": "UUID", "action": "expression", "payload": { "state": "Relaxed" } }` |
| POST `/commands` | `{ "id": "UUID", "action": "stop", "payload": {} }` |
| GET `/commands/<UUID>` | `{ "id": "UUID", "action": "speak", "status": "completed" }` |

Speech length is 1–300 nonblank characters. Expression states are Relaxed, Engaged, Excited, Stressed. Initial acknowledgement **must** match the request ID and have `status: "accepted"`. Never treat an HTTP 200 as physical completion. Duplicate retained IDs are idempotent and do not execute twice. IDs retain at most 100 entries; at most 16 commands may be pending. Reusing an evicted ID is unsupported; clients always generate fresh UUIDs.

Completion/cancellation events are exposed by polling the command resource every five seconds. Allowed states: accepted, completed, failed, cancelled. Backend transport timeout is three seconds and completion timeout is 30 seconds; missing/mismatched status becomes timed_out. A transport failure can leave execution uncertain; do not automatically retry a new command. Backend records accepted/failed history independently of the bridge. Stop calls `stopMovement` and `cancelAllTtsRequests`, cancels outstanding bridge commands and reports completed only for SDK invocation. That is **not verified physical stopping** or an emergency-stop system. Speech completes only on matching TTS UUID callbacks; SDK ERROR/NOT_ALLOWED fail and CANCELED cancels. Expression completes after changing the Android TextView; no physical movement is involved. Bridge timeout fails a still-pending command and requests TTS cancellation. SDK disconnect fails outstanding commands. Replay blocks all robot sends, including Stop; exit Replay to operate the robot.

## Build/install

Open `android-bridge` in Android Studio with JDK 17, Android SDK platform 35 and Gradle 8.9 (Android Gradle Plugin 8.7.3/Kotlin 2.0.21). Sync, build `:app:assembleDebug`, then install the APK on Temi via the vendor-supported development/ADB workflow. With an installed Gradle: `gradle -p android-bridge :app:assembleDebug`; install `android-bridge/app/build/outputs/apk/debug/app-debug.apk` using `adb install -r <path>`. A Gradle wrapper is not bundled; Android Studio/installed Gradle is required.

Minimum Android API 23, target API 28 for this local sideloaded demonstration; this is not a Play Store release. The SDK's manifest provider initializes Robot. Launch the bridge, enter token, Start bridge, and wait for actual SDK readiness. Keep the activity running; it is not a background/foreground service and shuts down the server when destroyed. Token is held only in memory. Enable/approve app skill permissions as required by the installed Temi Launcher. Configure the computer and robot on the same reachable LAN, reserve the robot address, and allow only the operator host to TCP 8080. The Python backend remains loopback-bound.

SDK 1.138.0 is pinned from the [official SDK installation reference](https://github.com/robotemi/sdk). Check its [release notes](https://github.com/robotemi/sdk/releases) and installed Launcher/firmware compatibility before deploying to a particular robot. The project uses [SDK readiness](https://github.com/robotemi/sdk/wiki), [TTS request UUID/status](https://github.com/robotemi/sdk/blob/master/sdk/src/main/java/com/robotemi/sdk/TtsRequest.kt), and [SDK speech/cancellation/stop](https://github.com/robotemi/sdk/blob/master/sdk/src/main/java/com/robotemi/sdk/Robot.kt). No claim of firmware compatibility has been physically verified here.

## Hardware verification

Build and install first; verify false/true readiness across robot disconnect/reconnect. Test authentication rejection, exact accepted ID, speech completion matching TTS UUID, a simple on-screen expression, duplicate-ID idempotency, stop/cancel during speech, missing completion timeout, bridge restart, and inaccessible-network behavior. Confirm no navigation/dance/movement commands exist. Verify physical stopping separately under vendor procedures; an HTTP stop does not establish it. Headset-derived estimates require explicit operator confirmation. Do not enable autonomous movement.
