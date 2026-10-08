import { describe, expect, it } from 'vitest';
import { appendHistory, MAX_SAMPLES, parseSnapshot } from './snapshot';
import type { EegSample } from '../types/dashboard';
const sample = (time: number): EegSample => ({ time, values: { AF3: 4200 }, interpolated: false });
const snapshot = {
  connections: Object.fromEntries(['cortex', 'headset', 'temi'].map(name => [name, { status: 'connected', message: 'Connected', checked_at: 100 }])),
  revision: 1, server_time: 100, status: { phase: 'streaming', message: 'Connected' },
  headset: { id: 'test', status: 'connected' }, session_id: 'test-session',
  streams: { eeg: { age_seconds: 0, observed_hz: 128 } }, rejected_streams: {},
  latest: { eeg: sample(1) }, eeg: [sample(1)], invalid_samples: 0, events: [],
};
describe('backend payload validation', () => {
  it('accepts channel amplitudes without altering them', () => {
    expect(parseSnapshot(JSON.stringify(snapshot)).eeg[0].values.AF3).toBe(4200);
  });
  it('rejects missing or malformed connectivity reports', () => {
    expect(() => parseSnapshot(JSON.stringify({ ...snapshot, connections: undefined }))).toThrow();
    expect(() => parseSnapshot(JSON.stringify({ ...snapshot, connections: { ...snapshot.connections, temi: { status: 'connected' } } }))).toThrow();
  });
  it('rejects malformed data', () => {
    expect(() => parseSnapshot('{}')).toThrow();
    expect(() => parseSnapshot(JSON.stringify({ ...snapshot, eeg: [{ ...sample(1), values: { AF3: 'bad' } }] }))).toThrow();
  });
  it('rejects malformed quality values', () => {
    expect(() => parseSnapshot(JSON.stringify({ ...snapshot, latest: { dev: { time: 1, values: { AF3: [] } } } }))).toThrow();
  });
});
describe('rolling EEG history', () => {
  it('deduplicates overlapping backend batches', () => {
    expect(appendHistory([sample(1), sample(2)], [sample(2), sample(3)])).toHaveLength(3);
  });
  it('removes samples outside the ten-second window', () => {
    expect(appendHistory([sample(1)], [sample(20)])).toEqual([sample(20)]);
  });
  it('caps memory even if samples arrive unusually quickly', () => {
    const result = appendHistory([], Array.from({ length: 5000 }, (_, i) => sample(i / 1000)));
    expect(result).toHaveLength(MAX_SAMPLES);
  });
});
