# Upstream review: what changed between our baseline and v0.21.7

Written for the Pi2/IoT fork sync. Everything below is measured with `git`/`gh` against
`NousResearch/hermes-agent` on the local merge worktree, not copied from a summary.

Status: the sync is **staged but not committed, not pushed and has no PR**. The worktree
`/media/matt/E/hermes-agent-iot` is on branch `sync/upstream-v0.21.7`, `HEAD` = `3b154b6814` (= the
current `pi2-lite` tip), with an in-progress merge of upstream `v0.21.7` (`MERGE_HEAD`
`71d34bad1045`). All 46 conflicts are resolved and staged; the fork-owned delta for 40 files is
re-applied in the working tree and still needs a re-stage before the merge commit. The fork version
moves `0.21.5.post2 -> 0.21.7.post1`; every doc pin (READMEs, Raspberry Pi manuals, `IOT_PROJECT.md`
— 8 markdown files) still names the last hardware-verified release `0.21.5.post2` until
`0.21.7.post1` has actually run on a Pi 2. Tag `iot-v0.21.7.post1`, the GitHub Release and the PyPI
publish stay staged behind that verification.

## Scope

| | |
| --- | --- |
| Our fork's baseline | `0.21.5.post2`, upstream tag `v2026.9.24` = commit `f97608f178` |
| Fork branch | `pi2-lite` (`3b154b6814` = `HEAD` of the sync branch before the merge) |
| Upstream target | **`v0.21.7`** (annotated tag object `00f69310e2`, tagger 2026-10-12T05:53:37Z) = commit `71d34bad10`, release published 2026-10-12T05:53:41Z; upstream's notes state **Release Date: October 11, 2026** |
| Upstream `main` tip | `41cd7b649d` (9 commits past the tag) when this review was written; re-checked 2026-10-13: `90292fe021`, 248 commits past the tag |
| Distance baseline → target | **9,957 upstream-only commits** (`git rev-list --count f97608f178..71d34bad10`; 9,621 non-merge) vs **160 fork-only commits** (`git rev-list --count 71d34bad10..HEAD`) |
| Merge result in the index | **9,888 files changed, +855,423 / −247,818** (`git diff --cached --shortstat`, rename detection on; 9,894 paths without rename collapse) |
| Conflicts | **46 paths**, all resolved (0 unmerged, no conflict markers; list from `.git/MERGE_MSG`) |
| Upstream's own window figures | `v0.21.6`: 8,867 non-merge commits / 8,342 files since our baseline; `v0.21.7`: 740 non-merge commits / 4,156 files (+86,775 / −26,980), 204 merged PRs, 69 closed issues since `v0.21.6` (upstream release notes, measured upstream at `818c13be1d` and `1fd1827726`) |

Upstream's own summary of what v0.21.7 ships for source installs: updates now follow tagged releases
(`hermes update --set-channel main` to keep following every commit), an *Update channel* switch in the
desktop app, signed reasoning that replays after `hermes chat --resume`, and an update-record fetch
that no longer 403s behind some regional firewalls. Security fixes carried in the window (all quoted
from upstream's own release notes): the Dashboard auth hardening reported by Tenable Research
(`X-Forwarded-For` rate-limit bypass, unbounded audit-log writes, no request-body cap on public
`/auth/` routes, native sign-in redirecting to a non-loopback callback — TRA-725…728), the repository
git-filter hardening (automatic git calls could run `clean`/`smudge`/`process` filters from an
untrusted repository's config before the first prompt), and the email-gateway `From` header spoofing
fix (a quoted display name could pass the allowlist).

## Fork divergence surface (what this merge must preserve)

Net difference between upstream `v2026.9.24` (`f97608f178`) and our pre-merge `pi2-lite`
(`3b154b6814`): **187 files, +19,286 / −2,158** (`git diff --shortstat f97608f178 3b154b6814`).
Largest areas: `tests/` 45, `contributors/` 26, repository root 21, `.github/` 19, `hermes_cli/` 16,
`scripts/` 13, `agent/` 11, `website/` 7. Upstream's window touched **9,905 files**, of which **89**
are also in our divergence surface (real conflict pressure); the remaining 98 fork files upstream did
not touch at all.

## Conflict ledger (46 paths)

Resolved by class, each verified against the merge index (`git diff :1: :2: :3:`) rather than by
picking a side:

**Superseded by upstream — the fork's hardening already exists upstream under a newer mechanism**

| path | why |
| --- | --- |
| `.github/workflows/ci.yml` | fork's inline fail-closed aggregator replaced by `scripts/ci/required_results.py`, which fails on every non-`success`, non-allowed-`skipped` result (stricter than the fork's rule) |
| `tools/lazy_deps.py` | upstream retired the runtime lazy installer: the module is a 26-line old-updater shim and `pm.ensure_import(<extra>)` is the only lazy surface, enforced by the new blocking `lazy-deps-guard.yml` |
| `scripts/install.ps1` | upstream's rewrite (1,449 lines) removed the PowerShell `$sdkMap` platform-SDK block and the `[web]` uvicorn hint the fork patched |
| `gateway/platforms/api_server.py` | fork's `version("hermes-agent-iot")` target no longer exists; upstream reads `version_info().base_version` |
| `hermes_cli/status.py`, `hermes_cli/doctor_tools.py` | the Vercel SDK messages the fork pinned were rewritten upstream |
| `tests/test_cmd_update.py`, `tests/test_windows_subprocess_no_window_flags.py`, `tests/agent/test_switch_model_rollback.py`, `tests/test_packaging_metadata.py` (partial) | upstream replaced or pruned the whole files; the fork hunks targeted removed helpers/blocks |
| `website/docs/developer-guide/gateway-monitoring.md` | the `[otlp]` install example the fork renamed no longer exists |

**Fork delta ported onto upstream's newer code**

| path | what was ported |
| --- | --- |
| `agent/agent_runtime_helpers.py`, `agent/chat_completion_helpers.py` | the fork's switch/fallback snapshot-restore deltas: the helpers upstream's own `except` blocks already called (but did not define) were reinstated, and the fork's field list merged with upstream's newer `_codex_reasoning_replay_enabled` entries |
| `hermes_cli/cli_info_mixin.py` | fork's runtime-configurable minimum context length, re-expressed inside upstream's newer `t()` strings |
| `hermes_cli/tools_config.py`, `toolsets.py`, `hermes_cli/main.py`, `tools/mqtt_tool.py` | the fork's MQTT toolset/category/provider registration and the `local-llama` provider flow; `tools/mqtt_tool.py` now installs its extra through `pm.ensure_import("mqtt")` |
| `.github/workflows/tests.yml`, `tests-os.yml`, `install-e2e.yml`, `label-rerun.yml` | fork's `ubuntu-latest` runners, `HERMES_TEST_WORKERS: 2`, 90-minute test timeout, `vars.IOT_RUN_UPSTREAM_E2E` opt-in for the e2e/e2e-upgrade lanes, the `ci.yml` filename fix and `fetch-depth: 0` for the release-tag picker |
| `tests/hermes_cli/{test_bang_shell_mode,test_chat_query_file,test_tools_config,test_update_autostash}.py`, `tests/test_project_metadata.py`, `tests/test_packaging_build_guard.py` | fork regression tests and packaging assertions re-placed into upstream's rewritten files |
| `tools/mqtt_tool.py`, `scripts/check_pi2_install_guards.py`, `tests/test_pi2_install_guards.py`, `tests/test_iot_packaging_profiles.py` | the fork's MQTT guard/tests retargeted from the retired `tools.lazy_deps` registry to the live `pm.ensure_import("mqtt")` surface — same policy, live authority |
| `README.md`, `README.es.md`, `README.zh-CN.md` | upstream's installer/Termux notes placed in the fork's upstream-install sections; version pins untouched |

Also resolved on the same policy: `.gitignore`, `contributors/emails/Cosmiclady@yandex.ru`,
`package-lock.json`, `pyproject.toml`, `uv.lock`, `apps/desktop/package.json`, `toolsets.py`,
`agent/monitoring/otlp_exporter.py`, `hermes_cli/{main,model_setup_flows,__init__}.py`,
`.github/workflows/{osv-scanner.yml,tests-os.yml}`,
`website/{docs/user-guide/features/voice-mode.md,i18n/zh-Hans/.../voice-mode.md}`,
`tests/hermes_cli/{test_doctor,test_model_switch_context_offload,test_update_yes_flag}.py`.

**Known, deliberate losses (recorded rather than hidden)**

- `tests/test_discord_voice_dependency_security.py`: upstream's rewrite removed the `install.ps1`
  `DISCORD_BOT_TOKEN` recovery triplets, which have no surviving host anywhere in the tree, so the one
  test asserting them was dropped. The surviving assertions (patched specs in pyproject's `messaging`
  extra and in `scripts/discord-voice-doctor.py`, no `discord.py[voice]` in those authorities, doctor
  never recommending `PyNaCl<1.6`) are kept.
- `tests/test_packaging_metadata.py`: upstream pruned the Termux/uvloop test the fork's 13-line
  adaptation lived in. The policy is still enforced by the fork's own guard
  (`scripts/check_pi2_install_guards.py` bans `uvloop`/`uvicorn[standard]` for the Pi2 profiles).
- READMEs: 4 of upstream's hunks rewrite sections the fork READMEs do not carry (Nous Portal provider
  list, Contributing/PM development setup), so they were not forced in.

## Fork invariants preserved

- `PyJWT[crypto]==2.15.0` and `urllib3>=2.8.0` floors, the documented `oauthlib` `exclude-newer`
  exception, the `h2>=4.4.1` override, and `pillow-heif` still absent from the dependency graph.
- `messaging` carries the explicit voice closure (`discord.py==2.7.1`, `PyNaCl==1.6.2`, `davey==0.1.4`)
  with no `discord.py[voice]` in that extra; `[tool.uv] override-dependencies` keeps `pynacl>=1.6,<1.7`.
- IoT profile extras (`cli`, `minimal`, `iot`, `rag`, `full`, `dev`, `mqtt`, `homeassistant`, `termux`,
  `termux-all`), the packaged `resources/profiles/*.yaml` Pi2 templates, the `hermes-iot` console script,
  the `modal`/`vercel` conflict pair, and every fork `exclude-newer-package` whitelist entry.
- `hermes_cli/__init__.py` keeps a real `__version__` literal (`0.21.7.post1`) alongside upstream's lazy
  install-stamp `__getattr__`, and `__release_date__` stays `2026.9.24` (the same value upstream ships
  at this tag).
- The fork's root `package.json` `overrides` block (35 entries) survives, with the direct `js-yaml`
  dependency raised to `4.3.2` so npm accepts the override (the fork's advisory fix), and
  `apps/desktop/package.json` re-pinned to the fork's security versions (`dompurify 3.4.16`,
  `katex 0.18.2`, `simple-git 4.0.2`, `electron 41.10.6`); upstream moved `electronVersion` into
  `electron-builder.config.cjs`, so the fork's `build.electronVersion` key is gone rather than lost.

Deliberate divergence worth naming for review: upstream moved its dev tooling to `[dependency-groups] dev`
while the fork keeps a `dev` extra; both feed one lockfile, so the group's colliding pins were aligned to
the fork (`httpx2 2.7.0 -> 2.12.0`, `ty 0.0.82 -> 0.0.21`).

## Local gates (measured on this worktree)

| gate | result | evidence |
| --- | --- | --- |
| Conflict resolution | 0 unmerged paths, 0 `*.rej` left in the tree, no `<<<<<<<` markers in `*.py`/`*.yml`/`*.toml`/`*.md` | `git diff --diff-filter=U` empty; `find . -name '*.rej'` empty |
| Affected-surface slice A (19 test files) | first run 2 failed / 170 passed / 17 errors → after fixing the two real defects it re-ran **165 passed, 31 subtests passed, 0 failed** | `~/.hermes/cache/scratch/sliceA.txt`, `sliceA2.txt` (2026-10-12) |
| Full `tests/scripts` + `tests/skills` slice B | **3201 passed / 154 skipped / 11 failed / 2 errors** in 27m27s; the 13 reds were re-run on the clean baseline and classified as pre-existing, not introduced by this merge | `~/.hermes/cache/scratch/sliceB.txt` (2026-10-12 17:39) |
| JS supply-chain guard | lifecycle-script check: 14 install-script package(s) seen, **0 new**; guard passed | `~/.hermes/cache/scratch/jsguard.txt` (2026-10-12 17:11) |
| Pi 2 install guard | `Pi2 install guard checks passed` (exit 0) | re-run 2026-10-13 09:38 via `.venv/bin/python scripts/check_pi2_install_guards.py` |
| Packaging / metadata / guard / security tests | **70 passed, 31 subtests passed, 0 failed** in 22.14s | `~/.hermes/cache/scratch/sync0217-gates-20261013-093832.log` |
| `pyproject.toml` parse | valid TOML: version `0.21.7.post1`, 67 extras, `dependency-groups` `dev`+`test`, 4 `tool.uv` overrides, 114 `exclude-newer-package` entries | `.venv/bin/python -c "tomllib.load(...)"` |
| Lock consistency | `uv lock --check` → rc 0, 352 packages resolved, worktree unchanged afterwards | `~/.hermes/cache/scratch/sync0217-lockcheck.log` |
| Structural no-loss check | the merge result drops 324 files and **all 324 are upstream's own deletions** (upstream's tree diff `f97608f178 → 71d34bad10` deletes 326); 0 files lost that upstream kept | NUL-safe `git ls-tree` / `git ls-files` set comparison against `backup/pi2-lite-before-upstream-sync-20261012` (= `3b154b6814`, 15,158 files) |
| Version / lock consistency | `hermes_cli/__init__.py` and `pyproject.toml` both `0.21.7.post1`; `uv.lock` carries the fork pins | `grep` on the worktree |
| Doc pins | 8 markdown files still name `0.21.5.post2` (unchanged by design) | `grep -rl` on the worktree |
| Index state before commit | after re-staging: 0 unstaged, 0 untracked (`git diff --quiet` clean), fork content present in the index (`__version__` literal, `pm.ensure_import("mqtt")`, `uv.lock` pins) | `git show :<path>` |

Still not covered here: a full `tests/` run on this worktree (the 2026-10-12 slices A/B above are the
closest evidence; the long `tests/scripts`+`tests/skills` slice B still carries its 13 pre-existing
reds), and a real Pi 2 install of `0.21.7.post1` (that happens after the release is published).

## Operational state of this branch

- Merge staged in the index: 9,888 files (rename-detection on) / 9,894 paths.
- Working tree carries the fork-owned delta for **40 files** (e.g. `hermes_cli/__init__.py` restores
  the `0.21.7.post1` literal that the staged upstream version serves lazily; `uv.lock`, the packaging
  tests, `scripts/check_pi2_install_guards.py`, the three READMEs).
  **A `git commit` right now would commit the index and drop that delta**, so those files must be
  re-staged first.
- `docs/upstream-review-v0.21.7.md` (this file) is written into the worktree but not yet committed.
- Backup ref `backup/pi2-lite-before-upstream-sync-20261012` is intact.

## Follow-ups

- Re-stage the 40 fork-delta files, re-run the Pi2 guard + packaging gates, then commit the merge
  non-force, push `sync/upstream-v0.21.7` and open the PR to `pi2-lite`.
- Physical Pi 2 verification of `0.21.7.post1` after the release is published; docs pins move only then.
- Upstream still declares an alias `discord = ["discord.py[voice]==2.7.1"]` extra; the vulnerable
  `PyNaCl<1.6` cap it would pull is neutralised by the `pynacl>=1.6,<1.7` override, and the live Discord
  path resolves through `pm.ensure_import("discord")`. Re-check when upstream drops or re-pins that extra.
- The retired `install.ps1` SDK-recovery triplets have no replacement host; if Windows recovery needs an
  equivalent, it belongs in the Python installer surface, not a fork patch to a rewritten script.
