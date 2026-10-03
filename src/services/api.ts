const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const api = new URL(base);
if (!['http:', 'https:'].includes(api.protocol)) throw new Error('VITE_API_BASE_URL must be an HTTP URL.');
export const liveUrl = new URL('/api/live', api);
liveUrl.protocol = api.protocol === 'https:' ? 'wss:' : 'ws:';
