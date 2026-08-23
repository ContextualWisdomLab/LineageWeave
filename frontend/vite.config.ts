/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    // Playwright owns e2e/ (npm run test:e2e); vitest must not import it.
    exclude: ['node_modules/**', 'e2e/**'],
  },
})
