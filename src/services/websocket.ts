/**
 * WebSocket service for real-time EEG data from the Python BrainBot backend.
 *
 * Connects to the local Python server (brainbot_main.py) which streams
 * Cortex data (com, met, sys) over WebSocket.
 *
 * Usage:
 *   const ws = useWebSocket();
 *   ws.connect('ws://localhost:8080');
 *   ws.send({ type: 'subscribe', streams: ['com', 'met', 'sys'] });
 */

export type StreamType = 'com' | 'met' | 'sys';

export interface CortexMessage {
  type: StreamType;
  data: Record<string, unknown>;
}

export interface WebSocketService {
  connect(url: string): void;
  disconnect(): void;
  send(message: unknown): void;
  onMessage(callback: (message: CortexMessage) => void): void;
  onConnect(callback: () => void): void;
  onDisconnect(callback: () => void): void;
  onError(callback: (error: Event) => void): void;
  isConnected(): boolean;
}

class WebSocketServiceImpl implements WebSocketService {
  private ws: WebSocket | null = null;
  private url: string | null = null;
  private messageCallbacks: ((message: CortexMessage) => void)[] = [];
  private connectCallbacks: (() => void)[] = [];
  private disconnectCallbacks: (() => void)[] = [];
  private errorCallbacks: ((error: Event) => void)[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;

  connect(url: string): void {
    this.url = url;
    this.reconnectAttempts = 0;

    try {
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.connectCallbacks.forEach((cb) => cb());
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as CortexMessage;
          this.messageCallbacks.forEach((cb) => cb(message));
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      this.ws.onclose = () => {
        this.disconnectCallbacks.forEach((cb) => cb());
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        this.errorCallbacks.forEach((cb) => cb(error));
      };
    } catch (err) {
      console.error('[WebSocket] Connection error:', err);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * this.reconnectAttempts;

    this.reconnectTimer = setTimeout(() => {
      if (this.url) {
        console.log(`[WebSocket] Reconnecting (attempt ${this.reconnectAttempts})...`);
        this.connect(this.url);
      }
    }, delay);
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.url = null;
  }

  send(message: unknown): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send: not connected');
    }
  }

  onMessage(callback: (message: CortexMessage) => void): void {
    this.messageCallbacks.push(callback);
  }

  onConnect(callback: () => void): void {
    this.connectCallbacks.push(callback);
  }

  onDisconnect(callback: () => void): void {
    this.disconnectCallbacks.push(callback);
  }

  onError(callback: (error: Event) => void): void {
    this.errorCallbacks.push(callback);
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

// Singleton instance
export const websocketService = new WebSocketServiceImpl();