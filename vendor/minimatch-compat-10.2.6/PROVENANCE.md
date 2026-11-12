# minimatch 10.2.6 — vendored runtime (Hermes IoT fork)

Not an official minimatch release. Official source: `isaacs/minimatch` v10.2.6 (commit `ded1bbd0`).

## Modifications

Two resource bounds from upstream **11.0.1** are backported for `GHSA-g3hv-75wg-m249` / `CVE-2026-118764`:

1. `firstPhasePreProcess` reads `braceExpandMax` (default 100_000) and stops growing `**` expansions at the budget.
2. `secondPhasePreProcess` skips the optional quadratic de-duplication above 1000 parts.

`main`, `module`, `types` and the root `exports` entry point at `compat/`, which keeps the interface the fork's previous compat tarball exposed: a callable CommonJS module, and an ESM default (the matcher) plus the named exports, `makeRe` included.

## Why vendored rather than a tarball dependency

pnpm `overrides` cannot point a *transitive* dependency at a remote tarball: `blockExoticSubdeps: true` rejects that on purpose (root dependencies may still be remote). A local `link:` override keeps the transitive remote surface at zero.

## Maintenance

Rebuild with `scripts/ci/build_vendored_minimatch.py --tarball <official tarball> --out <this directory>` when upstream ships a release the fork must carry. `tests/ci/test_pnpm_minimatch_compat.py` fails if the lockfile resolves any `minimatch` below 11.0.1 (the OSV fixed version) outside this directory.
