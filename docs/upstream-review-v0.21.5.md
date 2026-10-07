# Upstream review: what changed between our baseline and v0.21.5 (v2026.9.24)

Written for the Pi2/IoT fork sync. Everything below is measured with `git`/`gh` against
`NousResearch/hermes-agent`, not copied from a summary.

Status: the sync described here is **in review** (`sync/upstream-v2026.9.24`, PR to `pi2-lite`) and has
not been tagged or published. The fork version moves `0.21.4.post1 -> 0.21.5.post1`, and every doc pin
(README, manuals, `IOT_PROJECT.md`) still names the last hardware-verified release `0.21.4.post1` until
`0.21.5.post1` has actually run on a Pi 2. Tag `iot-v0.21.5.post1`, the GitHub Release and the PyPI
publish stay staged behind that verification.

## Scope

| | |
| --- | --- |
| Our fork's baseline | `v2026.9.21` (upstream tag, commit `d337b736aa`), fork version `0.21.4.post1` |
| Official install on this PC | `f97608f1` — updated to the target itself on 2026-10-07 |
| Upstream target (tag) | **`v0.21.5` / tag `v2026.9.24`** = `f97608f178d1ffeca59860195ab7da295f7c8e5f` (tag object `e3dd27ee`), released 2026-09-24 |
| Upstream `main` tip | `13dc3a73895aff1f823c1566bc1dd9b52fe35b65` (2026-10-07) |
| Commits in the window (baseline → tag) | **1,638** |
| Diff size (baseline → tag) | **4,828 files, +164,132 / −149,440** |
| Upstream's own window statement | since v0.21.4: 1,610 non-merge commits, 4,828 files (+164,132 / −149,440), 460 merged PRs, 475 closed issues; curated notes deferred to v0.22.0 |
| Fork side in the same window | 136 commits, 169 files; **52 files touched by both sides** |

Commit mix in the window: 755 `fix` · 298 `test` · 121 `feat` · 114 `chore` · 103 other · 77 `refactor` ·
48 `docs` · 37 `fmt` · 35 `perf` · 30 `catalog`. Subjects naming a CVE/GHSA/advisory/security/OSV issue: 4.

Area distribution (commit subjects): desktop 364 · catalog 223 · gateway 150 · plugin-catalog 96 ·
plugins 78 · agent 66 · config 58 · update 49 · memory 42 · cli 38 · skills 35 · kanban 33 · mcp 28 ·
state 27 · cron 21 · tools 21 · compression 17 · windows 15 · macos 9 · codex 8 · voice 5 · tts 3 ·
stt 3 · auth 2 · honcho 1.

## What is in it that matters for this fork

- **Agent core** — `agent/context_compressor.py` carries 28 upstream commits (+251 / −42) and is the file
  where the fork's configurable tool-context floor lives; this is the one conflict that needed a real
  union rather than a side pick. `conversation_compression.py` (12, +157 / −35), `agent_init.py` (9),
  `auxiliary_client.py` (6), `conversation_loop.py` (5), `run_agent.py` (6) and
  `agent_runtime_helpers.py` (5) are all files the fork also patches.
- **Compression/clipping surfaces** — the fork's Pi2 profiles depend on compaction firing at the right
  threshold on small windows, so the 28-commit rework of the trigger math is the highest-risk change in
  this window.
- **CLI** — `hermes_cli/web_server.py` (10, +76 / −37), `main.py` (5), `update_cmd.py` (6),
  `update_cmd_deps.py` (5, +198 / −63); the fork ships install/update guards, so movement here is the
  area most likely to need re-verification after a merge.
- **Tests were purged upstream in bulk** — 26 commits titled `test: purge low-value tests` (lanes
  py01–py20, js01–js06, each removing 156–624 entries). Five of this sync's eleven conflicts are exactly
  that shape: the fork's own additions inside files/blocks upstream deleted.
- **Nothing low-resource specific upstream.** A subject search over the window for
  `pi2|raspberry|armv7|armv6|low-resource|termux|musl|alpine|32-bit` returns **0** commits. Our fork is
  the only place that work lives, which is why the fork delta has to be carried through by hand.
- **Desktop is the largest area (364)** and the fork ships none of it; that weight is upstream-only and
  only matters where it touches shared manifests (`package-lock.json`, `apps/desktop/package.json`).

## Conflict map for this fork (the actual cost of syncing)

- Fork-only delta: **169 files**, of which 52 are also touched upstream.
- Upstream changed **4,828 files** between `v2026.9.21` and `v2026.9.24`.
- **Merge conflicts: 11 files** (the other 4,817 changed files merged automatically).

Upstream churn on the overlapping files where a mistake would hurt most:

| File | Upstream commits | Upstream diff |
| --- | --- | --- |
| `agent/context_compressor.py` | 28 | +251 / −42 |
| `agent/conversation_compression.py` | 12 | +157 / −35 |
| `pyproject.toml` | 12 | +16 / −12 |
| `tests/agent/test_context_compressor.py` | 11 | +134 / −451 |
| `.github/workflows/tests.yml` | 10 | +171 / −9 |
| `hermes_cli/web_server.py` | 10 | +76 / −37 |
| `agent/agent_init.py` | 9 | +42 / −35 |
| `agent/auxiliary_client.py` | 6 | +44 / −19 |
| `run_agent.py` | 6 | +29 / −15 |
| `agent/conversation_loop.py` | 5 | +43 / −30 |
| `agent/model_metadata.py` | 5 | +65 / −17 |
| `hermes_cli/main.py` | 5 | +31 / −18 |

Below five upstream commits but still overlapping (no judgement call needed this round):
`gateway/platforms/api_server.py`, `tools/lazy_deps.py`, `toolsets.py`, `hermes_cli/main_install_repair.py`,
`agent/chat_completion_helpers.py`, `.github/workflows/{docker,tests-os}.yml`, `.gitignore`,
`hermes_cli/{__init__,cli_info_mixin,tools_config}.py`, `nix/packages.nix`, `scripts/install.ps1`,
`uv.lock`, `package-lock.json`, `apps/desktop/package.json`, `website/docs/user-guide/features/voice-mode.md`,
plus the fork's own tests.

## Resolution policy used for the sync

1. `backup/pi2-lite-before-upstream-sync-20261007` ref created before touching anything.
2. Merge upstream `v2026.9.24` with `--no-ff` into a scratch worktree branch
   (`sync/upstream-v2026.9.24`) — no rebase, no force push, `pi2-lite` untouched until the PR merges.
3. `agent/context_compressor.py`: **union**. Kept the fork's `minimum_context_length` argument (its
   configurable floor) on upstream's rewritten call site, and took upstream's `_effective_threshold_cap()`
   helper instead of the fork's inline clamp.
4. Files upstream deleted but the fork modified (`tests/test_termux_all_extra_compat.py`,
   `tests/integration/test_voice_channel_flow.py`): the fork file is kept — they cover fork behaviour
   upstream has no reason to keep.
5. Five test conflicts where upstream's side is an **empty purge** and the fork's side is its own
   regression coverage: fork side kept, never deleted to make the merge green.
6. `pyproject.toml`: fork side for name/description and for the `dev`/`messaging` extras, which carry the
   fork's security pins (explicit discord voice closure, PyNaCl, `httpx2==2.12.0`).
7. `uv.lock`: upstream's 0.21.5 resolutions restored first, then only the fork pins re-applied with
   `uv lock` (`pillow-heif` removed for ARMv7, `httpx2 2.7.0 -> 2.12.0`).
8. Version fields move to `0.21.5.post1` (`hermes_cli/__init__.py` + release date `2026.9.24`,
   `pyproject.toml` project version and self-referencing extras, `uv.lock`, fork packaging tests).
   **Docs stay pinned at `0.21.4.post1`.**

Three merge residuals the local gates caught and the merge commit fixes (they are the reason the gates
are run before a PR, not after):

- `tests/test_packaging_build_guard.py` — fork test body, upstream import block: `tarfile`/`zipfile`
  were no longer imported (`NameError`).
- `tests/hermes_cli/test_model_switch_context_offload.py` — same shape for `asyncio`.
- `pyproject.toml` `[tool.uv.exclude-newer-package]` — the automatic merge dropped the fork's
  `hindsight-client = false` line, which reds
  `tests/test_packaging_metadata.py::test_exact_pinned_deps_exempt_from_exclude_newer`; restored and the
  lock regenerated.

## Verification on this branch (local, before the PR)

| Gate | Result |
| --- | --- |
| `uv lock --check` | rc=0 |
| `scripts/check_pi2_install_guards.py --repo .` | rc=0 |
| `check-case-collisions.py`, `check_compat_pointers.py`, `check_config_yaml_writers.py`, `check_profile_scope_patterns.py`, `check_subprocess_stdin.py`, `check_no_tmp_literals.py` | rc=0 each |
| focused set (24 files, incl. every conflicted file) | 1,137 passed / 4 failed — the 4 are the residuals above |
| the three fixed files after the fix | 18 passed / 0 failed |
| fork-owned test files (43 files) | 1,350 passed / 0 failed / 19 skipped |

Not yet done, and deliberately not claimed: `uv sync --locked` in CI, the JS/Rust/Nix lanes, and
**any** hardware verification. CI on the PR is the first full-suite run of this tree.

## Security-lane state on this branch (measured, then accepted)

The `OSV-Scanner` lane is **red on this branch**: the scan reports **42 packages affected by 115 known
vulnerabilities (9 critical / 47 high / 45 medium / 12 low / 2 unknown)** across `uv.lock` (278 packages)
and the four `package-lock.json` files, and this ref carries ≥100 open code-scanning alerts. Attribution was
measured before deciding anything:

| Measurement | Result |
| --- | --- |
| Open alerts on `pi2-lite` **before this sync** | 100 |
| Open alerts on `main` | 4 |
| `OSV-Scanner` history on `pi2-lite` | 2026-09-28 success → **2026-10-05 failure** (red before this work) |
| Flagged Python versions vs upstream's own `v2026.9.24` lock | identical — `urllib3 2.7.0`, `pyjwt 2.13.0`, `oauthlib 3.3.1` |
| Flagged JS versions vs upstream's lock | present upstream too — `axios 1.18.1`, `undici 7.29.0` |
| Required check on `pi2-lite`? | no (`All required checks pass`, `Pi2 install dependency guardrails`) |

Decision (2026-10-07): **stay byte-identical with upstream and accept the red**, consistent with how earlier
upstream-latency reds were handled, instead of diverging the fork's dependency graph. Recorded here for the
next cycle: `urllib3` and `pyjwt` do reach the Pi 2 install closure
(`requirements/pi2/{minimal,iot}.lock`) at upstream's chosen versions, so re-check whether upstream has
moved them before the next sync.

## Follow-ups (not in this PR)

- Physical Pi 2 verification of `0.21.5.post1` (isolated venv + isolated `HERMES_HOME`, `[minimal]`
  install from PyPI once published); the raw log is kept alongside the previous cycle's.
- Tag `iot-v0.21.5.post1`, GitHub Release and PyPI publish — staged behind that verification.
- Multi-language docs (`README.es.md`, `README.zh-CN.md`, `RASPBERRY_PI2_MANUAL*.md`) get the new version,
  PyPI digest, workflow URL and commit only after the release exists.
