#!/usr/bin/env node
/**
 * Behavioural checks for the vendored minimatch copies.
 *
 * `node --check` and marker grep only prove the text was edited; these assertions prove the
 * package still works as the interface the fork depends on AND that both
 * GHSA-g3hv-75wg-m249 bounds are actually in effect, for the CommonJS and ESM entries of both
 * vendored majors (9.x, 10.x).
 *
 * Needs `brace-expansion` resolvable (the vendor packages declare it). CI runs this after the
 * JS install; locally run it from a tree with node_modules, or from a temp copy:
 *
 *     npm i --prefix /tmp/mm-check brace-expansion@5.0.12
 *     NODE_PATH=/tmp/mm-check/node_modules node scripts/ci/check_vendored_minimatch.mjs
 */

import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'
import { readdirSync } from 'node:fs'
import path from 'node:path'
import process from 'node:process'

const repo = path.resolve(import.meta.dirname, '..', '..')
const require = createRequire(import.meta.url)

const packages = readdirSync(path.join(repo, 'vendor'))
  .filter((name) => name.startsWith('minimatch-compat-'))
  .sort()
  .map((name) => path.join('vendor', name))
assert.ok(packages.length > 0, 'no vendored minimatch package found under vendor/')

function checkApi(label, mm, named) {
  assert.equal(typeof mm, 'function', `${label}: default export must be callable`)
  assert.equal(typeof named.makeRe, 'function', `${label}: makeRe must exist`)
  assert.equal(typeof named.match, 'function', `${label}: match must exist`)
  assert.equal(typeof named.braceExpand, 'function', `${label}: braceExpand must exist`)
  assert.equal(typeof named.Minimatch, 'function', `${label}: Minimatch must exist`)
  assert.equal(typeof named.defaults, 'function', `${label}: defaults() helper must exist`)

  // Ordinary matching and makeRe keep working (the reason 11.0.1 is not a drop-in).
  assert.equal(mm('src/a.js', 'src/*.js'), true, `${label}: plain match`)
  assert.equal(mm('src/a.ts', 'src/*.js'), false, `${label}: negative match`)
  const re = named.makeRe('**/*.js')
  assert.ok(re instanceof RegExp, `${label}: makeRe returns a RegExp`)
  assert.equal(re.test('deep/nested/b.js'), true, `${label}: makeRe matches`)
  assert.equal(new named.Minimatch('**/*.md').match('a/b/c.md'), true, `${label}: Minimatch#match`)
}

function checkBraceExpandMaxGuard(label, named) {
  // The patched guard reads `braceExpandMax` (default 100_000) inside firstPhasePreProcess and
  // stops expanding `**` once globParts reaches the budget. The pre-11.0.1 code ignores the
  // option entirely, so the same call grows the list even at a budget of 1.
  const parts = ['a', '**', '..', 'b', 'c']
  const bounded = new named.Minimatch('a/**/../b/c', {}).firstPhasePreProcess([parts.slice()])
  assert.equal(bounded.length, 2, `${label}: default budget must expand (${JSON.stringify(bounded)})`)

  const capped = new named.Minimatch('a/**/../b/c', { braceExpandMax: 1 })
  const cappedOut = capped.firstPhasePreProcess([parts.slice()])
  assert.equal(
    cappedOut.length,
    1,
    `${label}: braceExpandMax=1 must not expand, got ${JSON.stringify(cappedOut)}`,
  )
  assert.deepEqual(cappedOut[0], parts, `${label}: capped run must leave the parts untouched`)
}

function checkLargePartsEarlyReturn(label, named) {
  // Above 1000 parts the patched code returns the input list unchanged instead of running the
  // optional quadratic de-duplication. That early return is observable by reference identity and
  // by cost: the unpatched code compares every pair (see checkAgainstControl).
  const input = Array.from({ length: 1200 }, (_, i) => ['a' + i])
  const started = process.hrtime.bigint()
  const out = new named.Minimatch('x', {}).secondPhasePreProcess(input)
  const elapsedMs = Number(process.hrtime.bigint() - started) / 1e6
  assert.equal(out, input, `${label}: >1000 parts must return the input list itself (early return)`)
  assert.ok(elapsedMs < 50, `${label}: early return took ${elapsedMs.toFixed(1)}ms`)
}

function checkAgainstControl(label, patched, control) {
  // Same inputs against the unpatched official build: the differences above must be real.
  const parts = ['a', '**', '..', 'b', 'c']
  const controlCapped = new control.Minimatch('a/**/../b/c', { braceExpandMax: 1 })
  const controlOut = controlCapped.firstPhasePreProcess([parts.slice()])
  assert.notEqual(
    controlOut.length,
    1,
    `${label}: control build unexpectedly honoured braceExpandMax; the guard would be untested`,
  )

  const big = Array.from({ length: 1200 }, (_, i) => ['a' + i])
  const started = process.hrtime.bigint()
  const controlBig = new control.Minimatch('x', {}).secondPhasePreProcess(big)
  const controlMs = Number(process.hrtime.bigint() - started) / 1e6
  assert.notEqual(controlBig, big, `${label}: control build unexpectedly early-returned`)

  const started2 = process.hrtime.bigint()
  new patched.Minimatch('x', {}).secondPhasePreProcess(big)
  const patchedMs = Number(process.hrtime.bigint() - started2) / 1e6
  console.log(
    `     control diff: firstPhase budget ignored (${controlOut.length} vs 1 parts), ` +
      `secondPhase ${controlMs.toFixed(1)}ms unpatched vs ${patchedMs.toFixed(1)}ms patched`,
  )
  assert.ok(
    patchedMs < controlMs,
    `${label}: patched secondPhase (${patchedMs.toFixed(1)}ms) must be cheaper than unpatched (${controlMs.toFixed(1)}ms)`,
  )
}

for (const rel of packages) {
  const dir = path.join(repo, rel)
  const version = path.basename(rel).replace('minimatch-compat-', '')
  const controlRoot = process.env.HERMES_MINIMATCH_CONTROL
  const control = controlRoot ? require(path.join(controlRoot, version)) : null

  const label = `${path.basename(rel)} (cjs)`
  const cjs = require(dir)
  checkApi(label, cjs, cjs)
  checkBraceExpandMaxGuard(label, cjs)
  checkLargePartsEarlyReturn(label, cjs)
  if (control) checkAgainstControl(label, cjs, control)

  const esmLabel = `${path.basename(rel)} (esm)`
  const esm = await import(pathToFileURL(path.join(dir, 'compat', 'index.mjs')).href)
  checkApi(esmLabel, esm.default, esm)
  checkBraceExpandMaxGuard(esmLabel, esm)
  checkLargePartsEarlyReturn(esmLabel, esm)
  if (control) checkAgainstControl(esmLabel, esm, control)

  console.log(`ok ${rel}: cjs+esm callable API, makeRe, braceExpandMax cap, >1000-parts early return`)
}

console.log('vendored minimatch: behavioural checks passed')
