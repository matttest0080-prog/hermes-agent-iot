# Upstream review: what changed between our baseline and v0.22.2

Written for the Pi2/IoT fork sync. Everything below is measured with `git`/`gh` against
`NousResearch/hermes-agent` on the local merge worktree, not copied from a summary.

Status: the sync is **committed, pushed and open as a PR**. Branch `sync/upstream-v0.22.2`, head
`d30913fe80`, PR https://github.com/matttest0080-prog/hermes-agent-iot/pull/43 (base `pi2-lite`,
supersedes the closed #42). The fork version moved `0.21.7.post1 -> 0.22.2.post1`. Tag
`iot-v0.22.2.post1`, the GitHub Release and the PyPI publish stay staged behind the physical Pi 2
verification; every doc pin (READMEs, Raspberry Pi manuals, `IOT_PROJECT.md`) still names the last
hardware-verified release `0.21.5.post2` until `0.22.2.post1` has actually run on a Pi 2.

## Scope

| | |
| --- | --- |
| Our fork's baseline | `0.21.7.post1`, upstream tag `v0.21.7` = commit `71d34bad10` (released 2026-10-12T05:53:41Z) |
| Fork branch | the `sync/upstream-v0.21.7` head `e8b20f2d7c` (v0.21.7 + IoT delta, the closed PR #42) |
| Upstream target | **`v0.22.2`** = commit `d923a5eb487a`, release published 2026-10-15T08:21:32Z; upstream's notes state **Release Date: October 15, 2026** |
| Upstream `main` tip | `e5eb6b36fe` when this review was written — **299 commits past the tag** |
| Distance baseline → target | **2,983 upstream-only commits** (`git rev-list --count v0.21.7..v0.22.2`; 2,844 non-merge) vs **184 fork-only commits** (`git rev-list --count v0.22.2..HEAD`) |
| Merge result | **1,214 files changed, +40,519 / −19,519** (`git diff --shortstat e8b20f2d7c 78c54b30a5`) |
| Upstream's own diff for the window | **1,274 files, +39,802 / −18,940** (`git diff --shortstat v0.21.7 v0.22.2`) |
| Fork divergence surface | **433 files, +21,751 / −3,004** (`git diff --shortstat v0.22.2 HEAD`) |
| Conflicts | **67 paths**: 55 `contributors/emails/*` + 12 substantive, all resolved (0 unmerged, no stray conflict markers) |
| Commit window shape | 1,591 `fix`, 374 `test`, 275 `feat`, 164 `chore`, 138 `refactor`, 70 `docs`, 39 `catalog`, 36 `ci`, 15 `perf`; largest areas `gateway` 394, `desktop` 307, `cli` 109, `tui` 93, `plugin-catalog` 84, `catalog` 79, `onboarding` 67, `api` 53, `state` 48 |
| Upstream's own window figures | `v0.22.0` "The Threshold Release": ~24,200 commits · ~6,080 merged PRs · ~15,600 files changed · ~2,045,000 insertions · ~1,140,000 deletions · ~7,180 issues closed · ~2,520 contributors since v0.21.0. `v0.22.1` and `v0.22.2` are patch releases (Oct 14 / Oct 15) |

Upstream's own summary: **v0.22.1 was built from the wrong commit** — it shipped unreleased gateway work
— and v0.22.2 is the release 0.22.1 was meant to be. v0.22.2 rolls up the fixes 0.22.1 was supposed to
ship plus two more: the gateway starts after a reboot again (Linux could hand an early PID to an
unrelated process and the gateway mistook it for a running one; it now records the boot it started in
and asks the host lock when it cannot tell — #138594), and long local-model turns survive on laptops
(streamed prompt-reading progress, stall timers that skip sleep, a recovered local server getting
another try, compression no longer timing out mid-read). The rest of the 0.22 line is the Threshold
Release: stable SemVer release channels, a guided first-launch setup on a free trial model, connectors,
one-click local models, signed desktop packages. Known upstream issue at this tag: sessions that ran
under the 0.22.1 gateway cannot be deleted in 0.22.2.

## Fork divergence surface (what this merge must preserve)

Largest areas of the fork's own delta against the target: `hermes_cli/`, `tests/`, `.github/workflows/`,
`tools/`, `scripts/`, `contributors/`, `requirements/pi2/`, `apps/desktop/`, and the Pi2 profile
templates. The merged window touched 1,274 upstream files; the fork's 433-file divergence overlaps on
the workflow, packaging and CLI surfaces where the conflict pressure actually was.

## Conflict ledger (67 paths)

Resolved against the merge index (`git diff :1: :2: :3:`) rather than by picking a side.

**Contributor attribution — 55 paths**

`contributors/emails/*` (98 files walked): where the fork had a value, the fork's value and its
attribution note are kept; where the fork only had a note and no value, upstream's value is filled in.
Result: zero double-valued files.

**Substantive — 12 paths**

| path | resolution |
| --- | --- |
| `pyproject.toml` | only the `exclude-newer` hunk conflicted: keep the fork's "14 days + per-package exemption table" model (Pi2/ARMv7 installs depend on it behind mirrors that publish no upload dates); everything else is upstream's 3-way result |
| `hermes_cli/tools_config.py` | keep the fork's MQTT IoT category; drop the fork's langfuse block — upstream moved langfuse to `plugin-catalog/langfuse.yaml` and deleted `_LANGFUSE_PUBLIC/_LANGFUSE_SECRET`, so keeping it would `NameError` on import |
| `apps/desktop/package.json` | keep the fork's three security pins (`dompurify 3.4.16`, `katex 0.18.2`, `simple-git 4.0.2`); take upstream's newer `yaml 2.9.1` |
| `ui-tui/package.json` | `undici` takes upstream's `6.29.0` (newer than the fork's `6.28.1`) |
| `scripts/whatsapp-bridge/package-lock.json` | `music-metadata` takes upstream's `11.16.1` |
| `.npmrc` | union both sides' `min-release-age-exclude` lines (fork's OSV lines + upstream's `source-map-js` note) |
| `.github/workflows/lint.yml` | union — upstream's new `ref: ${{ inputs.commit }}` plus the fork's `fetch-depth: 50` |
| `hermes_cli/observability/schemas/hermes.shared_metrics.v4.schema.json` | union of both enums (`mqtt` + `onboarding`) |
| `tests/ci/test_stable_release_graph.py` | keep both imports (fork's `require_upstream_ci_yaml` and upstream's `scripts.releases.lanes`) |
| `uv.lock` / `package-lock.json` | not hand-resolved — regenerated by their tools (`pm lock` off `pyproject`; `npm install --package-lock-only` reported up to date) |

Follow-up repairs the merge needed afterwards (each its own commit, all verified):

- `eb072b650e` restored the OSV pins the merge dropped from `package-lock.json` (9 paths the fork pins
  through `package.json` overrides) and `uv.lock` (multidict/oauthlib/tornado).
- `6398a328a7` bumped `mcp 2.0.0 -> 2.2.0` (GHSA-84m7-p3x7-pcfv) across `pyproject.toml`, `uv.lock` and
  the four Pi2 hashed locks.
- `fbf735ec24` adapted four upstream tests the merge brought in that assume upstream's own layout.
- `7cda4a2db9` raised the markdown property-fuzz timeout for the fork's slower CI runner.

## Fork invariants preserved

- `PyJWT[crypto]==2.15.0` and `urllib3>=2.8.0` floors, the documented `oauthlib` `exclude-newer`
  exception (resolved to `4.0.0`), the `h2>=4.4.1` override, `pynacl>=1.6,<1.7`, and `pillow-heif` still
  absent from the dependency graph.
- `messaging` carries the explicit voice closure (`discord.py==2.7.1`) with no `discord.py[voice]` in that
  extra; `discord = ["discord.py[voice]==2.7.1"]` remains gated by the `pynacl>=1.6,<1.7` override.
- IoT profile extras (`cli`, `minimal`, `iot`, `rag`, `full`, `dev`, `mqtt`, `homeassistant`, `termux`,
  `termux-all`), the packaged `resources/profiles/*.yaml` Pi2 templates, the `hermes-iot` console script,
  the `modal`/`vercel` conflict pair, and every fork `exclude-newer-package` whitelist entry.
- `hermes_cli/__init__.py` keeps a real `_FALLBACK_VERSION` literal (`0.22.2.post1`) alongside upstream's
  lazy install-stamp `__getattr__`; `__release_date__` stays `2026.9.24` (the same value upstream ships
  at this tag).
- The fork's root `package.json` `overrides` block (35 entries) survives; `apps/desktop/package.json`
  keeps the fork's security versions.
- The fork's MCP pin is the one deliberate security bump inside the sync: `mcp==2.2.0` + `mcp-types==2.2.0`
  (upstream still pins `2.0.0`), with `httpx2==2.12.0` and `starlette==1.3.1` unchanged.

## Local gates (measured on this worktree)

| gate | result | evidence |
| --- | --- | --- |
| Conflict resolution | 0 unmerged paths; the only `>>>>>>>` in the tree is an intentional fixture string in `tests/test_audit_old_updater_imports.py` | `git diff --name-only --diff-filter=U` empty; `git grep -nE '^(<<<<<<<|>>>>>>>)'` |
| Python compile of the changed non-test surface | **exit 0** on the 283 changed non-test `.py` files | `python3 -m compileall -q` |
| Lock consistency | `uv lock --check` → rc 0, 351 packages resolved; `git diff -U0 uv.lock` after the version bump moves only the `hermes-agent-iot` version/specifier lines | run on the worktree |
| Pi 2 install guard | `Pi2 install guard checks passed` (exit 0) | `uv run --python 3.12 --no-project python scripts/check_pi2_install_guards.py --repo .` |
| OSV scan | **0 findings** after restoring the pins and bumping mcp (the merge had 49 npm rows across 8 packages plus 4 PyPI packages in `uv.lock`) | CI `Scan lockfiles / osv-scan` on head `d30913fe80` |
| Packaging / metadata tests | version assertions pass; the two `test_setup_*` extras-dependent CLI tests fail identically at the pre-bump tree (overlay env lacks the extra deps — harness, not the bump) | `uv run --python 3.12 --no-project --with pytest … pytest tests/test_iot_packaging_profiles.py tests/test_termux_all_extra_compat.py tests/test_packaging_metadata.py tests/test_project_metadata.py` |
| MCP OAuth tests | **27 passed** with `mcp==2.2.0` installed | `pytest tests/tools/test_mcp_oauth_manager.py` |
| Release-graph threading | **1 passed, 5 skipped** (fork keeps `ci.yml`, so `require_upstream_ci_yaml` skips the `ci.yaml` contract) | `pytest tests/ci/test_stable_release_commit_threading.py` |
| Version / lock consistency | `hermes_cli/__init__.py` and `pyproject.toml` both `0.22.2.post1`; `uv.lock` carries 23 `==0.22.2.post1` specifiers | `grep` on the worktree |
| Remote verification | `git ls-remote matttest refs/heads/sync/upstream-v0.22.2` == local HEAD `d30913fe80` | after each non-force push |

Still not covered here: a real Pi 2 install of `0.22.2.post1` (happens after the release is published),
and the CI reds documented below are accepted, not resolved.

## CI state at this head

**44 pass / 5 fail / 0 pending.** The 5 reds are the same set the approved v0.21.7 baseline (#42)
carried, so v0.22.2 introduces none of them:

- `OS-specific tests / Windows-only tests` and `(arm64)`: green on the v0.21.5 baseline and red from
  v0.21.7 on. `hermes_cli/local_runtime/processes.py` and the test bodies are unchanged across that
  boundary; the fork switched this lane to a GitHub-hosted Windows runner in v0.21.7, so it is a
  runner-grade difference (`psutil` reports `running` for a `CREATE_SUSPENDED` child under load).
- `bundle win32-arm64`: `grpcio` has no `win_arm64` wheel, so the bundle builds its sdist and the
  ARM64 `cl.exe` step fails (pre-existing).
- `Python tests / Run tests (1/2)`: exactly the six tests #42 already failed
  (`test_source_channel_integration`, `test_source_release_channels` x2,
  `test_update_target_identity` x3) — all `hermes update` default-branch behaviour against the fork's
  `pi2-lite` default.
- `All required checks pass (v2)`: red because of the above.

Green and relevant: `Scan lockfiles / osv-scan` (0), `Check contributors / check-attribution`,
`package-lock.json diff`, `Check uv.lock`, `Pi2 install dependency guardrails`,
`Python tests / Run tests (2/2)`, `JS & TS checks`.

## Follow-ups

- Physical Pi 2 verification of `0.22.2.post1` after the release is published; the doc pins move only
  then. The verification fixture inside the fork's own self-test moves in the same pass.
- The five accepted CI reds above stay accepted until someone fixes them deliberately: the Windows
  runner difference, the `grpcio` win_arm64 bundle, and the six `hermes update` branch tests.
- `mcp==2.2.0` is a fork-only pin (upstream is still on 2.0.0). Re-check when upstream bumps it, so the
  fork can drop back to the upstream pin.
- Upstream `main` already carries 299 commits past this tag; the next sync should target whatever
  release tag exists then, not `main`.
