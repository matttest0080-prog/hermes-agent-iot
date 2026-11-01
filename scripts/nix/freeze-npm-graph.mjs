// Consume the already reviewed lock graph after importNpmLock removes semver
// overrides and rewrites tarballs to Nix store paths. Never resolve new versions.
import { readFileSync, renameSync, writeFileSync } from 'node:fs'
import { isAbsolute, join, posix, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const fields = ['dependencies', 'devDependencies', 'optionalDependencies']

function targetFor(packages, location, name) {
  for (let at = location; ; at = posix.dirname(at) === '.' ? '' : posix.dirname(at)) {
    const target = packages[`${at ? `${at}/` : ''}node_modules/${name}`]
    if (target) return target
    if (!at) return undefined
  }
}

export function freezeManifest(manifest, location, packages) {
  const result = structuredClone(manifest)
  for (const field of fields) {
    if (!result[field]) continue
    for (const [name, spec] of Object.entries(result[field])) {
      // Local links and aliases retain their identity, not a registry name.
      if (/^(file:|link:|workspace:|npm:)/.test(spec)) continue
      const target = targetFor(packages, location, name)
      // Platform-specific optional trees can be absent from the lock.
      if (!target || target.link || target.version === undefined) continue
      if (typeof target.version !== 'string' || !target.version) {
        throw new Error(`Invalid locked version for ${location}: ${name}`)
      }
      result[field][name] = target.version
    }
  }
  return result
}

export function freezeLock(lock) {
  if (!lock.packages || typeof lock.packages !== 'object' || !lock.packages['']) {
    throw new Error('A workspace package-lock with a root package is required')
  }
  return {
    ...lock,
    packages: Object.fromEntries(
      Object.entries(lock.packages).map(([location, manifest]) => [
        location,
        freezeManifest(manifest, location, lock.packages)
      ])
    )
  }
}

function workspacePaths(root, lock) {
  return Object.keys(lock.packages).filter(location => {
    if (!location || location.split('/').includes('node_modules')) return false
    if (isAbsolute(location) || location.split(/[\\/]/).includes('..')) {
      throw new Error(`Invalid workspace path: ${location}`)
    }
    return true
  }).map(location => ({ location, path: join(root, location, 'package.json') }))
}

const readJson = path => JSON.parse(readFileSync(path, 'utf8'))
const jsonText = value => `${JSON.stringify(value, null, 2)}\n`

export function prepare(root) {
  // Only the disposable Nix hook's staging tree is writable, never a checkout.
  readJson(join(root, '.package.json.orig'))
  readJson(join(root, '.package-lock.json.orig'))
  const lockPath = join(root, 'package-lock.json')
  const lock = readJson(lockPath)
  const frozen = freezeLock(lock)
  const workspaces = workspacePaths(root, lock).map(({ location, path }) => {
    const original = readFileSync(path, 'utf8')
    return { path, original, frozen: freezeManifest(JSON.parse(original), location, lock.packages) }
  })
  for (const workspace of workspaces) {
    writeFileSync(`${workspace.path}.nix-orig`, workspace.original, { flag: 'wx' })
  }
  for (const workspace of workspaces) writeFileSync(workspace.path, jsonText(workspace.frozen))
  writeFileSync(lockPath, jsonText(frozen))
}

export function restore(root) {
  const workspaces = workspacePaths(root, readJson(join(root, 'package-lock.json')))
  // Validate every backup before replacing any manifest.
  for (const { path } of workspaces) readJson(`${path}.nix-orig`)
  for (const { path } of workspaces) renameSync(`${path}.nix-orig`, path)
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const [action, root = process.cwd()] = process.argv.slice(2)
  if (action === 'prepare') prepare(resolve(root))
  else if (action === 'restore') restore(resolve(root))
  else throw new Error('Usage: freeze-npm-graph.mjs prepare|restore [Nix build root]')
}
