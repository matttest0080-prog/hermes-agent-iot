import { spawnSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const script = process.env.JS_SUPPLY_CHAIN_GUARD || fileURLToPath(new URL('../scripts/check_js_supply_chain.py', import.meta.url))
const key = 'package.json#devDependencies#compat'
const url = 'https://example.invalid/releases/v1.0.0/compat.tgz'
const integrity = `sha512-${Buffer.alloc(64, 1).toString('base64')}`
const save = (path, value) => writeFileSync(path, JSON.stringify(value))

function fixture(mutate = () => {}) {
  const root = mkdtempSync(join(tmpdir(), 'hermes-artifact-pin-'))
  mkdirSync(join(root, 'scripts'))
  const manifest = { name: 'fixture', devDependencies: { compat: url } }
  const lock = { lockfileVersion: 3, packages: {
    '': structuredClone(manifest),
    'node_modules/compat': { name: '@fixture/compat', version: '1.0.0', resolved: url, integrity }
  } }
  // Even a legacy name-only exception must not authorize a different URL/hash.
  const baseline = { pinned_exceptions: [key], lifecycle: [],
    artifact_pins: { [key]: { url, integrity } } }
  mutate({ manifest, lock, baseline })
  save(join(root, 'package.json'), manifest)
  save(join(root, 'package-lock.json'), lock)
  save(join(root, 'scripts/js-supply-chain-baseline.json'), baseline)
  return root
}
const run = (root, args = []) => spawnSync(process.env.HERMES_PYTHON || 'python3',
  [script, '--repo', root, ...args], { encoding: 'utf8', timeout: 10_000 })

describe('content-pinned HTTPS artifacts', () => {
  it('accepts only the reviewed root URL and actual locked SHA512, including a package alias', () => {
    const root = fixture()
    const result = run(root)
    expect(result.status, result.stdout + result.stderr).toBe(0)
    expect(result.stdout).toContain('guard passed')
    expect(run(root, ['--update']).status).toBe(0)
    const saved = JSON.parse(readFileSync(join(root, 'scripts/js-supply-chain-baseline.json'), 'utf8'))
    expect(saved.artifact_pins[key]).toEqual({ url, integrity })
    expect(saved.pinned_exceptions).not.toContain(key)
    expect(run(root).status).toBe(0)
  })

  it.each([
    ['changed URL', ({ manifest, lock }) => {
      const changed = 'https://example.invalid/releases/v2.0.0/compat.tgz'
      manifest.devDependencies.compat = changed
      lock.packages[''].devDependencies.compat = changed
      lock.packages['node_modules/compat'].resolved = changed
    }],
    ['changed locked hash', ({ lock }) => { lock.packages['node_modules/compat'].integrity = `sha512-${Buffer.alloc(64, 2).toString('base64')}` }],
    ['changed resolved source', ({ lock }) => { lock.packages['node_modules/compat'].resolved = 'https://other.invalid/compat.tgz' }],
    ['missing content hash', ({ lock }) => { delete lock.packages['node_modules/compat'].integrity }],
    ['missing root lock declaration', ({ lock }) => { delete lock.packages[''].devDependencies.compat }],
    ['missing review', ({ baseline }) => { baseline.artifact_pins = {} }],
    ['malformed reviewed hash', ({ baseline }) => { baseline.artifact_pins[key].integrity = 'sha512-not-base64!' }],
    ['non-SHA512 review', ({ baseline }) => { baseline.artifact_pins[key].integrity = 'sha256-a' }],
    ['insecure URL', ({ manifest, lock, baseline }) => {
      const insecure = url.replace('https:', 'http:')
      manifest.devDependencies.compat = insecure
      lock.packages[''].devDependencies.compat = insecure
      lock.packages['node_modules/compat'].resolved = insecure
      baseline.artifact_pins[key].url = insecure
    }]
  ])('rejects %s rather than trusting a package-name exception', (_label, mutate) => {
    const result = run(fixture(mutate))
    expect(result.status, result.stdout + result.stderr).toBe(1)
    expect(result.stdout).toContain(`VIOLATION ${key}`)
  })

  it('baseline update cannot automatically approve an unknown remote URL', () => {
    const root = fixture(({ baseline }) => { baseline.artifact_pins = {} })
    expect(run(root, ['--update']).status).toBe(0)
    const result = run(root)
    expect(result.status).toBe(1)
    expect(result.stdout).toContain(`VIOLATION ${key}`)
  })
})
