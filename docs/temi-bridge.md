# Optional Temi integration

The current dashboard monitors the headset and displays mental commands. It does not trigger robot movement automatically. Existing randomly selected mood-driven motion and mock robot output were removed.

Temi's native SDK runs in an Android app on the robot. The Python bridge client requires a separately installed app/server exposing the contract below. These are application-defined endpoints, not built-in Temi URLs.

Set `TEMI_BRIDGE_URL` to a base URL such as `http://192.168.1.100:8080/api`. Set `TEMI_BRIDGE_TOKEN` if your bridge requires bearer authentication. Both remain backend configuration.

| Local backend route | Bridge request | SDK responsibility |
|---|---|---|
| `POST /api/temi/speak`, JSON `{ "text": "Hello" }` | `POST <base>/speak`, same JSON | Perform text-to-speech using the SDK |
| `POST /api/temi/stop` | `POST <base>/stop`, JSON `{}` | Invoke SDK stop movement |

The client accepts successful HTTP status codes and reports command acceptance, not physical completion. An unconfigured bridge returns 503. Network errors or rejected commands return 502. Speech input is restricted to 1–300 characters. These endpoints are accessible through the local backend's interactive `/docs` page; the EEG dashboard has no misleading robot-connection badge.

Movement integration still needs a defined contract for bounded commands, acknowledgments, completion, cancellation, and robot-side heartbeat expiry. An actual emergency-stop state is separate from movement-in-progress. Verify SDK speed coefficients against physical speed on the actual robot, preserve obstacle protection, and test in a clear supervised area before enabling EEG-driven motion. A stop HTTP call alone does not provide a complete emergency-stop mechanism.

References:

- [Official Temi SDK](https://github.com/robotemi/sdk)
- [Temi developers](https://www.robotemi.com/developers/)
- [Temi official REST API](https://openapi-docs.robotemi.com/)

Temi also documents a cloud REST API requiring PRO access and an organization access token. This application does not implement that API; it is a different integration route and is not a drop-in implementation of these local bridge endpoints.
