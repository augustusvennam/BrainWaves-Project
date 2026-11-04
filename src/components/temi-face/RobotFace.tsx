import { useEffect, useState } from 'react';
import { websocketService, backendUrl, type CortexMessage, type ConnectionStatus } from '../../services/websocket';

type Emotion = 'Happy' | 'Sad' | 'Neutral' | 'Angry' | 'Anxious';

const EMOTIONS: Record<string, { emotion: Emotion; bg: string; face: string }> = {
  push:   { emotion: 'Happy',   bg: '#fef3c7', face: '/faces/happy.png' },
  pull:   { emotion: 'Sad',     bg: '#dbeafe', face: '/faces/sad.png' },
  neutral:{ emotion: 'Neutral', bg: '#f3f4f6', face: '/faces/neutral.png' },
  lift:   { emotion: 'Angry',   bg: '#ff3e3e', face: '/faces/angry.png' },
  drop:   { emotion: 'Anxious', bg: '#f0abfc', face: '/faces/anxious.png' },
};

const DEFAULT: { emotion: Emotion; bg: string; face: string } = {
  emotion: 'Neutral', bg: '#f3f4f6', face: '/faces/neutral.png',
};

export function RobotFace() {
  const [command, setCommand] = useState<string>('');
  const [power, setPower] = useState<number | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  useEffect(() => {
    const offStatus = websocketService.onStatus(setStatus);
    const offMessage = websocketService.onMessage((message: CortexMessage) => {
      if (message.type === 'state') {
        const cmd = message.data.command as { act?: string; pow?: number } | undefined;
        if (cmd && cmd.act) {
          setCommand(cmd.act);
          setPower(typeof cmd.pow === 'number' ? cmd.pow : null);
        } else {
          // The backend clears stale commands itself; show idle.
          setCommand('');
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
    <div
      className="flex min-h-screen w-full flex-col items-center justify-center gap-6 px-6 transition-colors duration-500"
      style={{ background: spec.bg }}
    >
      {status !== 'connected' && (
        <div className="absolute top-4 text-sm text-(--text-tertiary)">
          {status === 'connecting' ? 'Connecting to backend…' : 'Disconnected from backend'}
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
      <h1 className="text-5xl font-semibold tracking-tight text-(--text-ink)">
        {spec.emotion}
      </h1>
      {power !== null && (
        <p className="text-lg text-(--text-subtle)">
          Intensity {power.toFixed(2)}
        </p>
      )}
    </div>
  );
}

export default RobotFace;