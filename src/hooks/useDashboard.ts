import { useEffect, useState } from 'react';
import { liveUrl } from '../services/api';
import { appendHistory, parseSnapshot } from '../services/snapshot';
import type { EegSample, Snapshot } from '../types/dashboard';

export function useDashboard() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [history, setHistory] = useState<EegSample[]>([]);
  const [connection, setConnection] = useState('connecting');
  const [error, setError] = useState('');
  useEffect(() => {
    let disposed = false;
    let socket: WebSocket;
    let retry: number;
    let lastMessage = Date.now();
    let session: string | null = null;
    let attempts = 0;
    function connect() {
      if (disposed) return;
      setConnection('connecting');
      socket = new WebSocket(liveUrl);
      lastMessage = Date.now();
      socket.onmessage = event => {
        if (disposed) return;
        try {
          const next = parseSnapshot(event.data);
          lastMessage = Date.now();
          attempts = 0;
          if (`${next.session_id}:${next.epoch ?? 0}` !== session) {
            session = `${next.session_id}:${next.epoch ?? 0}`;
            setHistory(appendHistory([], next.eeg, 30));
          } else {
            setHistory(current => appendHistory(current, next.eeg, 30));
          }
          setSnapshot(previous => {
            const same = previous?.epoch === next.epoch && previous?.session_id === next.session_id;
            const combined = [...(same ? previous?.metric_history ?? [] : []), ...(next.metric_history ?? [])];
            const newest = combined.at(-1)?.time ?? 0;
            return {...next, metric_history: combined.filter(s => s.time >= newest-300).slice(-2048)};
          });
          setConnection('connected');
          setError('');
        } catch {
          setError('Invalid data received from backend. Waiting for a valid update.');
        }
      };
      socket.onerror = () => setError('Backend unavailable. Start the backend and check VITE_API_BASE_URL.');
      socket.onclose = () => {
        if (disposed) return;
        setConnection('unavailable');
        setSnapshot(null);
        setHistory([]);
        session = null;
        retry = window.setTimeout(connect, Math.min(1000 * 2 ** attempts++, 10000));
      };
    }
    connect();
    // Detect half-open connections as well as explicit close events.
    const watchdog = window.setInterval(() => {
      if (Date.now() - lastMessage > 10000) {
        setError('Backend stopped sending updates. Reconnecting.');
        socket.close();
      }
    }, 1000);
    return () => {
      disposed = true;
      window.clearTimeout(retry);
      window.clearInterval(watchdog);
      socket.close();
    };
  }, []);
  return { snapshot, history, connection, error };
}
