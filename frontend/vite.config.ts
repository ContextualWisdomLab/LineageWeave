import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { configDefaults } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    // The App-level jsdom suites render the whole workspace; on slower
    // developer machines a single test crosses the 5s default while the
    // same file passes on CI. Give them headroom without skipping work.
    testTimeout: 15000,
    setupFiles: ['./src/setupTests.ts'],
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
})
