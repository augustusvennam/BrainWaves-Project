import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    plugins: [react()],
    server: { host: 'localhost', port: Number(env.FRONTEND_PORT || 3000), strictPort: true },
    preview: { host: 'localhost', port: Number(env.FRONTEND_PORT || 3000), strictPort: true },
  };
});
