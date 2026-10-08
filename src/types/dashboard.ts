export interface Sample {
  time: number;
  values: Record<string, number | string | boolean | null>;
  interpolated?: boolean;
}
export interface EegSample {
  time: number;
  values: Record<string, number>;
  interpolated: boolean;
}
export interface ConnectionStatus {
  status: 'unknown' | 'connecting' | 'connected' | 'disconnected' | 'unconfigured' | 'unavailable';
  message: string;
  checked_at: number | null;
}
export interface Snapshot {
  connections: Record<'cortex' | 'headset' | 'temi', ConnectionStatus>;
  revision: number;
  server_time: number;
  status: { phase: string; message: string };
  headset: { id: string; status: string } | null;
  session_id: string | null;
  streams: Record<string, { age_seconds: number | null; observed_hz: number | null }>;
  rejected_streams: Record<string, string>;
  latest: Record<string, Sample>;
  eeg: EegSample[];
  invalid_samples: number;
  events: { time: number; message: string }[];
}
