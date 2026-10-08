import type { EegSample, Snapshot } from '../types/dashboard';

function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function number(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function parseSnapshot(raw: string): Snapshot {
  const value: unknown = JSON.parse(raw);
  if (!object(value) || !number(value.revision) || !number(value.server_time) ||
    !object(value.status) || typeof value.status.phase !== 'string' || typeof value.status.message !== 'string' ||
    !(value.session_id === null || typeof value.session_id === 'string') ||
    !(value.headset === null || (object(value.headset) && typeof value.headset.id === 'string' && typeof value.headset.status === 'string')) ||
    !object(value.streams) || !object(value.rejected_streams) || !object(value.latest) ||
    !Array.isArray(value.eeg) || value.eeg.length > 256 || !Array.isArray(value.events) || value.events.length > 40 ||
    !number(value.invalid_samples)) throw new Error('Malformed backend snapshot.');
  if (!object(value.connections)) throw new Error('Missing connection status.');
  for (const name of ['cortex', 'headset', 'temi']) {
    const connection = value.connections[name];
    if (!object(connection) || !['unknown', 'connecting', 'connected', 'disconnected', 'unconfigured', 'unavailable'].includes(String(connection.status)) ||
      typeof connection.message !== 'string' || !(connection.checked_at === null || number(connection.checked_at))) {
      throw new Error('Malformed connection status.');
    }
  }
  for (const sample of value.eeg) {
    if (!object(sample) || !number(sample.time) || !object(sample.values) || typeof sample.interpolated !== 'boolean' ||
      !Object.values(sample.values).every(number)) throw new Error('Malformed EEG sample.');
  }
  for (const sample of Object.values(value.latest)) {
    if (!object(sample) || !number(sample.time) || !object(sample.values) ||
      !Object.values(sample.values).every(v => v === null || typeof v === 'string' || typeof v === 'boolean' || number(v))) throw new Error('Malformed metric sample.');
  }
  for (const stream of Object.values(value.streams)) {
    if (!object(stream) || !(stream.age_seconds === null || number(stream.age_seconds)) ||
      !(stream.observed_hz === null || number(stream.observed_hz))) throw new Error('Malformed stream status.');
  }
  if (!Object.values(value.rejected_streams).every(v => typeof v === 'string')) throw new Error('Malformed stream errors.');
  for (const event of value.events) {
    if (!object(event) || !number(event.time) || typeof event.message !== 'string') throw new Error('Malformed event.');
  }
  return value as unknown as Snapshot;
}

export const HISTORY_SECONDS = 10;
export const MAX_SAMPLES = 4096;
export function appendHistory(history: EegSample[], incoming: EegSample[]): EegSample[] {
  const lastTime = history.at(-1)?.time ?? -Infinity;
  const fresh = incoming.filter(sample => sample.time > lastTime);
  const combined = [...history, ...fresh];
  const newest = combined.at(-1)?.time;
  return newest === undefined ? [] : combined.filter(sample => sample.time >= newest - HISTORY_SECONDS).slice(-MAX_SAMPLES);
}
