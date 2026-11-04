import { useEffect, useState } from "react";
import {
  websocketService,
  backendUrl,
  type CortexMessage,
  type ConnectionStatus,
} from "../../services/websocket";
import ShapeGrid from "../ShapeGrid";
import happyFace from "./faces/happy.png";
import sadFace from "./faces/sad.png";
import neutralFace from "./faces/neutral.png";
import angryFace from "./faces/angry.png";
import anxiousFace from "./faces/anxious.png";

type Emotion = "Happy" | "Sad" | "Neutral" | "Angry" | "Anxious";

const EMOTIONS: Record<string, { emotion: Emotion; bg: string; face: string }> =
  {
    push: { emotion: "Happy", bg: "#fef3c7", face: happyFace },
    pull: { emotion: "Sad", bg: "#dbeafe", face: sadFace },
    neutral: { emotion: "Neutral", bg: "#f3f4f6", face: neutralFace },
    lift: { emotion: "Angry", bg: "#ff3e3e", face: angryFace },
    drop: { emotion: "Anxious", bg: "#f0abfc", face: anxiousFace },
  };

const DEFAULT: { emotion: Emotion; bg: string; face: string } = {
  emotion: "Neutral",
  bg: "#f3f4f6",
  face: neutralFace,
};

export function RobotFace() {
  const [command, setCommand] = useState<string>("");
  const [power, setPower] = useState<number | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  useEffect(() => {
    const offStatus = websocketService.onStatus(setStatus);
    const offMessage = websocketService.onMessage((message: CortexMessage) => {
      if (message.type === "state") {
        const cmd = message.data.command as
          | { act?: string; pow?: number }
          | undefined;
        if (cmd && cmd.act) {
          setCommand(cmd.act);
          setPower(typeof cmd.pow === "number" ? cmd.pow : null);
        } else {
          // The backend clears stale commands itself; show idle.
          setCommand("");
          setPower(null);
        }
      }
    });
    // Connect back to the host that served this page, so the Temi reaches the
    // laptop's backend instead of its own loopback address.
    websocketService.connect(backendUrl());
    return () => {
      offStatus();
      offMessage();
      websocketService.disconnect();
    };
    // Empty deps on purpose: the service reconnects internally. Re-running this
    // effect on every status change would tear down and re-open the socket.
  }, []);

  const spec = EMOTIONS[command] ?? DEFAULT;

  return (
    <div style={{ width: "100%", height: "1080px", position: "relative" }}>
      <ShapeGrid
        shape="square"
        direction="diagonal"
        lineColor="#2a2734"
        hoverColor="#ffffff"
        hoverFillColor="#ffffff"
        fillOpacity={0.15}
        cellSize={40}
        speed={0.5}
        tiltX={0}
        tiltY={0}
        rainbow={false}
        lineWidth={1}
        radius={1.5}
        trail={0.6}
        glow={0.35}
        twinkle={0}
        fade={1}
        clickCascade
        intro
      />

      <div className="absolute top-3 left-3 text-sm text-(--text-tertiary)">
        {status !== "connected" && (
          <div>
            {status === "connecting"
              ? "Connecting to backend…"
              : "Disconnected from backend"}
          </div>
        )}
      </div>
      <div className="absolute top-[40%] left-[45%] text-sm text-(--text-tertiary) text-center">
        <img
          src={spec.face}
          alt={spec.emotion}
          className="h-64 w-64 object-contain drop-shadow-lg"
          onError={(e) => {
            // Fall back to an emoji if the face file isn't present yet.
            const target = e.currentTarget;
            target.style.display = "none";
            const next = document.createElement("div");
            next.className = "text-9xl";
            next.textContent =
              spec.emotion === "Happy"
                ? "🙂"
                : spec.emotion === "Sad"
                  ? "🙁"
                  : "😐";
            target.parentElement?.insertBefore(next, target);
          }}
        />
        <h1 className="text-5xl font-semibold tracking-tight text-(--text-ink) mt-3">
          {spec.emotion}
        </h1>
        {power !== null && (
          <p className="text-lg text-(--text-subtle)">
            Intensity {power.toFixed(2)}
          </p>
        )}
      </div>
    </div>
  );
}

export default RobotFace;
