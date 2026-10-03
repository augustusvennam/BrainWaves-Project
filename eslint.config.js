import js from '@eslint/js';
import ts from 'typescript-eslint';
export default ts.config(
  { ignores: ['dist/**', 'node_modules/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  { files: ['src/**/*.{ts,tsx}'], languageOptions: { globals: { window: 'readonly', document: 'readonly', WebSocket: 'readonly', URL: 'readonly', HTMLCanvasElement: 'readonly', ResizeObserver: 'readonly' } } },
  { files: ['scripts/*.mjs', 'vite.config.ts'], languageOptions: { globals: { process: 'readonly', console: 'readonly' } } },
);
