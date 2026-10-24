/** Native WebSocket transport; reconnects until explicitly disconnected. */
export type StreamType = 'met' | 'pow' | 'dev' | 'eq' | 'state' | 'pong';
export interface CortexMessage {
  type: StreamType;
  data: Record<string, unknown>;
}
type Callback<T> = (value: T) => void;
class WebSocketService {
  private ws: WebSocket | null = null;
  private url: string | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private attempts = 0;
  private messages = new Set<Callback<CortexMessage>>();
  private connects = new Set<() => void>();
  private disconnects = new Set<() => void>();
  private errors = new Set<Callback<Event>>();
  private add<T>(set: Set<T>, callback: T) { set.add(callback); return () => { set.delete(callback); }; }
  onMessage(cb: Callback<CortexMessage>) { return this.add(this.messages, cb); }
  onConnect(cb: () => void) { return this.add(this.connects, cb); }
  onDisconnect(cb: () => void) { return this.add(this.disconnects, cb); }
  onError(cb: Callback<Event>) { return this.add(this.errors, cb); }
  isConnected() { return this.ws?.readyState === WebSocket.OPEN; }
  connect(url: string) {
    this.disconnect();
    this.url = url;
    this.attempts = 0;
    this.open();
  }
  private open() {
    if (!this.url) return;
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      if (this.ws !== ws) return;
      this.attempts = 0;
      this.connects.forEach(cb => cb());
    };
    ws.onmessage = event => {
      if (this.ws !== ws) return;
      try {
        const message: CortexMessage = JSON.parse(event.data);
        this.messages.forEach(cb => cb(message));
      } catch { console.warn('Invalid backend message'); }
    };
    ws.onerror = event => { if (this.ws === ws) this.errors.forEach(cb => cb(event)); };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      this.disconnects.forEach(cb => cb());
      if (this.url) this.timer = setTimeout(() => this.open(), Math.min(1000 * 2 ** this.attempts++, 10000));
    };
  }
  disconnect() {
    this.url = null;
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const old = this.ws;
    this.ws = null;
    old?.close();
  }
  send(message: unknown) { if (this.isConnected()) this.ws?.send(JSON.stringify(message)); }
}
export const websocketService = new WebSocketService();
