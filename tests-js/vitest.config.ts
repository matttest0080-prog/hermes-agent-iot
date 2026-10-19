import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['**/*.test.ts', '**/*.test.mjs'],
    // These suites shell out to real git and build temp trees. vitest's 5s
    // default made `update-ui` (source probe) and `bundle-smoke-metadata`
    // (channel smoke) time out intermittently on a loaded CI runner — the same
    // two files, run after run. Assertions are unchanged; only the deadline
    // moves.
    testTimeout: 30_000,
  },
})
