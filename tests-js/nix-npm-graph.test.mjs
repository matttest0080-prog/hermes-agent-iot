import { execFileSync, spawnSync } from 'node:child_process'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

import { freezeLock, freezeManifest, prepare } from '../scripts/nix/freeze-npm-graph.mjs'

const save = (path, value) => writeFileSync(path, `${JSON.stringify(value, null, 2)}\n`)

describe('integrity-pinned Nix npm graph', () => {
  it('freezes overridden edges using nearest installed packages without changing artifacts or peers', () => {
    const lock = {
      lockfileVersion: 3,
      packages: {
        '': {},
        workspace: { dependencies: { b: '1.0.0', local: 'file:../local', alias: 'npm:b@1' } },
        'node_modules/a': {
          dependencies: { b: '^1' }, optionalDependencies: { absent: '^1' },
          peerDependencies: { b: '^1' }, version: '1.0.0', resolved: 'file:/store/a', integrity: 'sha512-a'
        },
        'node_modules/a/node_modules/b': { version: '3.0.0', resolved: 'file:/store/b3', integrity: 'sha512-b3' },
        'node_modules/b': { version: '2.0.0', resolved: 'file:/store/b2', integrity: 'sha512-b2' }
      }
    }
    const before = structuredClone(lock)
    const frozen = freezeLock(lock)
    expect(frozen.packages.workspace.dependencies).toEqual({ b: '2.0.0', local: 'file:../local', alias: 'npm:b@1' })
    expect(frozen.packages['node_modules/a'].dependencies.b).toBe('3.0.0')
    expect(frozen.packages['node_modules/a'].optionalDependencies).toEqual({ absent: '^1' })
    expect(frozen.packages['node_modules/a'].peerDependencies).toEqual({ b: '^1' })
    for (const [path, original] of Object.entries(lock.packages)) {
      expect(frozen.packages[path].resolved).toBe(original.resolved)
      expect(frozen.packages[path].integrity).toBe(original.integrity)
      expect(frozen.packages[path].version).toBe(original.version)
    }
    expect(lock).toEqual(before)
    expect(freezeLock(frozen)).toEqual(frozen)
    expect(freezeManifest({ dependencies: { b: 'file:/store/b2' } }, '', lock.packages))
      .toEqual({ dependencies: { b: 'file:/store/b2' } })
  })

  it('rejects missing lock graphs and refuses to mutate a checkout without hook backups', () => {
    for (const lock of [{}, { packages: null }, { packages: {} }]) expect(() => freezeLock(lock)).toThrow()
    const root = mkdtempSync(join(tmpdir(), 'hermes-nix-refusal-'))
    save(join(root, 'package.json'), { name: 'untouched' })
    const before = readFileSync(join(root, 'package.json'))
    expect(() => prepare(root)).toThrow()
    expect(readFileSync(join(root, 'package.json'))).toEqual(before)
  })

  it('installs a security-overridden workspace completely offline and restores its original manifest', () => {
    const root = mkdtempSync(join(tmpdir(), 'hermes-nix-offline-'))
    const app = join(root, 'app')
    mkdirSync(join(app, 'workspace'), { recursive: true })
    const env = {
      ...process.env, HOME: root, USERPROFILE: root,
      npm_config_userconfig: join(root, 'empty.npmrc'),
      npm_config_cache: join(root, 'cache'), npm_config_offline: 'true',
      npm_config_registry: 'http://127.0.0.1:9', npm_config_audit: 'false', npm_config_fund: 'false'
    }
    const npmCli = process.env.npm_execpath
    if (!npmCli) throw new Error('Run the suite through npm so its pinned CLI is available')
    const npm = (args, cwd = app) => spawnSync(process.execPath, [npmCli, ...args], {
      cwd, env, encoding: 'utf8', timeout: 20_000
    })
    const pack = (name, version, dependencies = {}) => {
      const source = join(root, name)
      mkdirSync(source)
      save(join(source, 'package.json'), { name, version, dependencies, main: 'index.js' })
      writeFileSync(join(source, 'index.js'), name === 'edge-a' ? "module.exports = require('edge-b')" : 'module.exports = 2')
      const result = npm(['pack', '--ignore-scripts', '--json', '--pack-destination', root], source)
      expect(result.status, result.stdout + result.stderr).toBe(0)
      return `file:${join(root, JSON.parse(result.stdout)[0].filename)}`
    }
    const a = pack('edge-a', '1.0.0', { 'edge-b': '1.0.0' })
    const b = pack('edge-b', '2.0.0')
    const manifest = { name: 'nix-fixture', version: '1.0.0', private: true, workspaces: ['workspace'],
      dependencies: { 'edge-a': a }, overrides: { 'edge-b': b } }
    const workspace = join(app, 'workspace', 'package.json')
    save(workspace, { name: 'edge-w', version: '1.0.0', dependencies: { 'edge-b': '1.0.0' } })
    const originalWorkspace = readFileSync(workspace)
    save(join(app, 'package.json'), manifest)
    const generated = npm(['install', '--package-lock-only', '--ignore-scripts', '--offline'])
    expect(generated.status, generated.stdout + generated.stderr).toBe(0)
    const originalLock = JSON.parse(readFileSync(join(app, 'package-lock.json'), 'utf8'))
    save(join(app, '.package.json.orig'), manifest)
    save(join(app, '.package-lock.json.orig'), originalLock)
    delete manifest.overrides // importNpmLock must remove these to avoid EOVERRIDE with file: specs.
    save(join(app, 'package.json'), manifest)
    // Match importNpmLock's local-workspace rewrite too, not just its tarballs.
    const storeWorkspace = join(root, 'pinned-source', 'workspace')
    mkdirSync(storeWorkspace, { recursive: true })
    writeFileSync(join(storeWorkspace, 'package.json'), originalWorkspace)
    const rewrittenLock = structuredClone(originalLock)
    rewrittenLock.packages['node_modules/edge-w'].resolved = `file:${storeWorkspace}`
    delete rewrittenLock.packages['node_modules/edge-w'].link
    save(join(app, 'package-lock.json'), rewrittenLock)
    const refused = npm(['install', '--ignore-scripts', '--offline'])
    expect(refused.status).not.toBe(0)
    expect(refused.stderr).toContain('ENOTCACHED')
    const helper = fileURLToPath(new URL('../scripts/nix/freeze-npm-graph.mjs', import.meta.url))
    execFileSync(process.execPath, [helper, 'prepare', app], { env })
    const installed = npm(['install', '--ignore-scripts', '--offline'])
    expect(installed.status, installed.stdout + installed.stderr).toBe(0)
    expect(execFileSync(process.execPath, ['-p', 'require("edge-a")'], { cwd: app, env, encoding: 'utf8' }).trim()).toBe('2')
    expect(JSON.parse(readFileSync(join(app, 'node_modules/edge-a/package.json'), 'utf8')).dependencies['edge-b']).toBe('1.0.0')
    const frozen = JSON.parse(readFileSync(join(app, 'package-lock.json'), 'utf8'))
    for (const [path, original] of Object.entries(originalLock.packages)) {
      expect(frozen.packages[path]?.integrity).toBe(original.integrity)
      expect(frozen.packages[path]?.version).toBe(original.version)
    }
    execFileSync(process.execPath, [helper, 'restore', app], { env })
    expect(readFileSync(workspace)).toEqual(originalWorkspace)
  }, 30_000)
})
