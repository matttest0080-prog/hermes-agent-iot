import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import semver from 'semver'
import { expect, test } from 'vitest'

test('website postcss and its nanoid stay pinned above their reviewed security floors', () => {
  const pkg = JSON.parse(readFileSync(fileURLToPath(new URL('../website/package.json', import.meta.url)), 'utf8'))
  const override = pkg.overrides.postcss
  expect(semver.valid(override['.'])).not.toBeNull()
  expect(semver.valid(override.nanoid)).not.toBeNull()
  expect(semver.satisfies(override['.'], '>=8.5.29 <9')).toBe(true)
  expect(semver.satisfies(override.nanoid, '>=3.3.20 <4')).toBe(true)
})
