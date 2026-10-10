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
  epoch?: number;
  sequence?: number;
  feed_dropped?: number;
  counters?: Record<string, number>;
  filtered_eeg?: EegSample[];
  metric_history?: Sample[];
  participant?: {id: string | null; phase: string; message: string; valid_samples: number; baseline: Record<string, number>; estimate: {state: string; scores: Record<string, number>; contributions: Record<string, number>}};
  recording?: {active: boolean; replay: boolean; replay_error?: string | null; replay_finished?: boolean; file: string | null; loss: number; filter: {enabled: boolean; settings: string; sample_rate: number | null}};
  profiles?: {items: {name: string}[]; current: {name?: string; loadedByThisApp?: boolean}; training: string; training_action?: string | null; training_event?: string | null};
  commands?: {id: string; action: string; status: string; time: number}[];
  connections: Record<'cortex' | 'headset' | 'temi', ConnectionStatus>;
  revision: number;
  server_time: number;
  status: { phase: string; message: string };
  headset: { id: string; status: string; settings?: {eegRate?: number} } | null;
  session_id: string | null;
  streams: Record<string, { age_seconds: number | null; observed_hz: number | null }>;
  rejected_streams: Record<string, string>;
  latest: Record<string, Sample>;
  eeg: EegSample[];
  invalid_samples: number;
  events: { time: number; message: string }[];
}
