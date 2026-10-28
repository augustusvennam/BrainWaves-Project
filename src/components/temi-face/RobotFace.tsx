import { useEffect, useState } from 'react';
import { websocketService, type CortexMessage } from '../../services/websocket';

type Emotion = 'Happy' | 'Sad' | 'Neutral';

const EMOTIONS: Record<string, { emotion: Emotion; bg: string; face: string }> = {
  push:   { emotion: 'Happy',   bg: '#fef3c7', face: '/faces/happy.png' },
  pull:   { emotion: 'Sad',     bg: '#dbeafe', face: '/faces/sad.png' },
  neutral:{ emotion: 'Neutral', bg: '#f3f4f6', face: '/faces/neutral.png' },
};

const DEFAULT: { emotion: Emotion; bg: string; face: string } = {
  emotion: 'Neutral', bg: '#f3f4f6', face: '/faces/neutral.png',
};

export function RobotFace() {
  const [command, setCommand] = useState<string>('');
  const [power, setPower] = useState<number | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const offConnect = websocketService.onConnect(() => setConnected(true));
    const offDisconnect = websocketService.onDisconnect(() => {
      setConnected(false);
      setCommand('');
      setPower(null);
    });
    const offMessage = websocketService.onMessage((message: CortexMessage) => {
      if (message.type === 'state') {
        const cmd = message.data.command as { act?: string; pow?: number } | undefined;
        if (cmd && cmd.act) {
          setCommand(cmd.act);
          setPower(typeof cmd.pow === 'number' ? cmd.pow : null);
        } else if (connected) {
          // Source went stale — show idle.
          setCommand('');
          setPower(null);
        }
      }
    });
    // Connect back to the host that served this page, so the Temi reaches the
    // laptop's backend instead of its own loopback address.
    const backendHost = typeof window !== 'undefined' && window.location.hostname
      ? window.location.hostname
      : '127.0.0.1';
    websocketService.connect(`ws://${backendHost}:8080`);
    return () => {
      offConnect();
      offDisconnect();
      offMessage();
      websocketService.disconnect();
    };
  }, [connected]);

  const spec = EMOTIONS[command] ?? DEFAULT;

  return (
    <div
      className="flex min-h-screen w-full flex-col items-center justify-center gap-6 px-6 transition-colors duration-500"
      style={{ background: spec.bg }}
    >
      {!connected && (
        <div className="absolute top-4 text-sm text-[var(--text-tertiary)]">
          Connecting to backend…
        </div>
      )}
      <img
        src={spec.face}
        alt={spec.emotion}
        className="h-64 w-64 object-contain drop-shadow-lg"
        onError={(e) => {
          // Fall back to an emoji if the face file isn't present yet.
          const target = e.currentTarget;
          target.style.display = 'none';
          const next = document.createElement('div');
          next.className = 'text-9xl';
          next.textContent = spec.emotion === 'Happy' ? '🙂' : spec.emotion === 'Sad' ? '🙁' : '😐';
          target.parentElement?.insertBefore(next, target);
        }}
      />
      <h1 className="text-5xl font-semibold tracking-tight text-[var(--text-ink)]">
        {spec.emotion}
      </h1>
      {power !== null && (
        <p className="text-lg text-[var(--text-subtle)]">
          Intensity {power.toFixed(2)}
        </p>
      )}
    </div>
  );
}

export default RobotFace;