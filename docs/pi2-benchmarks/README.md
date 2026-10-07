# Raspberry Pi 2 footprint baselines

Reference measurements of the **Pi2 (Raspberry Pi 2 Model B, ARMv7)** so that
footprint regressions are visible as numbers instead of impressions. Each file
is the raw JSON produced by `scripts/pi2_benchmark.py` on real hardware; nothing
here is estimated or extrapolated.

## Baselines

| Baseline | Version measured | Profile | Install source |
| --- | --- | --- | --- |
| `pi2-bench-0.21.3.post1.json` | `hermes-agent-iot 0.21.3.post1` | `minimal` | public PyPI (`pip install 'hermes-agent-iot[minimal]==0.21.3.post1'`) |
| `pi2-bench-0.21.4.post1.json` | `hermes-agent-iot 0.21.4.post1` | `minimal` | public PyPI wheel, `pip download` + SHA-256 checked on the device |
| `pi2-bench-0.21.4.post1-run2.json` | same release, same venv, run repeated ~30 s later | `minimal` | second sample — the run-to-run noise floor used below |
| `pi2-bench-0.21.5.post1.json` | `hermes-agent-iot 0.21.5.post1` | `minimal` | public PyPI wheel, `pip download` + index SHA-256 checked on the device |

Hardware/OS for all files: Raspberry Pi 2 Model B (`armv7l`, ARMv7 rev 5),
Raspbian trixie, CPython 3.13.5, 921 MiB RAM, 921 MiB swap, SD card.

Committed copies are the raw run JSON with `/home/pi2` collapsed to `~` (the same
treatment as the older files); nothing else is edited. Raw on-device digests for
the 0.21.4.post1 pair: run 1
`61431fac42583323e18a471762a01c2d4cce35e5e94233506c80c3d42559fd99`, run 2
`59dcfe901e55e9abda63bacf1a17f076d854effb25fdbd801d15997d82a3f796`; for
`pi2-bench-0.21.5.post1.json`,
`f9932f58bd6f124d9bb3c9f5d682b1c8ca228c2326927b006cf42f9cd6123f60`.

## What the numbers say (0.21.5.post1)

One sample, `--quick` (no model leg). Cold-start import cost, a fresh interpreter
per module, against the 0.21.4.post1 run on the same board:

| Module | import | peak RSS | vs 0.21.4.post1 |
| --- | --- | --- | --- |
| `hermes_cli.iot_cli` | 0.68 s | 16.8 MiB | −0.02 s, −48 KiB — noise |
| `agent.agent_init` | 5.32 s | 35.6 MiB | +0.54 s (+11 %), +1,288 KiB (+3.7 %) |
| `tools.registry` | 0.34 s | 16.8 MiB | +0.02 s — noise |

Console entry point measured in this run:

| Command | wall | peak RSS | exit | vs 0.21.4.post1 |
| --- | --- | --- | --- | --- |
| `hermes-iot profile show` | 1.05 s | 13.1 MiB | 0 | −0.01 s — flat |

Two caveats before reading a regression into that middle row: this run passed a
single `--cli-cmd`, so the `hermes --version` and `python -c pass` floors the
0.21.4 files measured are not repeated here, and it was captured at loadavg
1.2–2.0 against 0.16 for the 0.21.4 pair — the board was busier. +0.54 s / +1.3 MiB
on the heaviest module is inside what a two-sample comparison at that load
difference can produce; a repeat run on an idle board is what would settle it.

## What the numbers say (0.21.4.post1)

Cold-start import cost, fresh interpreter per module (`peak_rss_kb` is that
interpreter's high-water mark), against the archived 0.21.3.post1 baseline:

| Module | import | peak RSS | vs 0.21.3.post1 |
| --- | --- | --- | --- |
| `hermes_cli.iot_cli` | 0.70 s | 16.9 MiB | +0.01 s (+2 %) — noise |
| `agent.agent_init` | **4.79 s** | **34.3 MiB** | **+0.92 s (+24 %), +5,704 KiB (+19.4 %)** |
| `tools.registry` | 0.32 s | 16.9 MiB | −0.01 s (−3 %) — noise |

Console entry points, measured by wrapping each command in a clean parent
process:

| Command | wall | peak RSS | exit | vs 0.21.3.post1 |
| --- | --- | --- | --- | --- |
| `hermes-iot profile show` | 1.06 s | 13.2 MiB | 0 | −0.20 s (faster) |
| `hermes --version` | 3.38 s | 23.1 MiB | 0 | −0.01 s — flat |
| `python -c pass` (interpreter floor) | 0.15 s | 9.1 MiB | 0 | flat |

**The only number that moved is `agent.agent_init`**: +0.92 s and +5.7 MiB of
peak RSS on cold import, ~24 % slower and ~19 % heavier than 0.21.3.post1. It is
not measurement noise — the repeat run 30 s later
(`pi2-bench-0.21.4.post1-run2.json`) reproduced it within 0.18 s and 4 KiB, while
every other record reproduced within 0.02 s / 4 KiB, i.e. the floor on this board
is ~1 %.

Note what did *not* move: `hermes --version` is flat even though `agent_init` got
0.92 s heavier, which shows the thin CLI entry points never import `agent_init`.
The regression lands on paths that do load the agent (agent runs, gateway, TUI),
not on `--version` or `profile show`.

Environment for both files: 921 MiB RAM (713 MiB available during run 1),
921 MiB swap (881 MiB free — the 0.21.3.post1 file was captured with only 705 MiB
free, which is background state, not a release difference), ~5.7 GiB free on
`$HOME`, loadavg 0.16.

## What the numbers say (0.21.3.post1)

Cold-start import cost, measured in a fresh interpreter per module
(`peak_rss_kb` is that interpreter's high-water mark):

| Module | import | peak RSS |
| --- | --- | --- |
| `hermes_cli.iot_cli` | 0.68 s | 16.7 MiB |
| `agent.agent_init` | **3.87 s** | 28.7 MiB |
| `tools.registry` | 0.33 s | 16.7 MiB |

Console entry points, measured by wrapping each command in a clean parent
process (so the peak RSS belongs to the command, not to a long-lived shell):

| Command | wall | peak RSS | exit |
| --- | --- | --- | --- |
| `hermes-iot profile show` | 1.26 s | 13.1 MiB | 0 |
| `hermes --version` | 3.39 s | 22.8 MiB | 0 |
| `python -c pass` (interpreter floor) | 0.15 s | 9.1 MiB | 0 |

Reading these together: importing the agent costs ~3.9 s and lands at ~29 MiB,
so the ~3.4 s `hermes --version` is essentially "start Python, import the CLI
stack, print, exit". On an x86 host the same `agent.agent_init` import measures
~0.16 s, i.e. **ARMv7 is roughly 20x slower on cold import** — that is the
number to watch when adding import-time work to the CLI path.

`wrapper_overhead_s` in each CLI record is the measurement wrapper's own cost
(fork/exec + reading `VmHWM`), not part of the command; subtract it when
comparing against timings taken another way.

## Reproducing

On the Pi (isolated venv, no sudo needed):

```sh
python3 -m venv ~/hermes-iot-bench
~/hermes-iot-bench/bin/pip install "hermes-agent-iot[minimal]==<version>"
export HERMES_HOME=~/hermes-bench-home          # keep the run off your real config
~/hermes-iot-bench/bin/hermes-iot setup --profile minimal
scp scripts/pi2_benchmark.py pi2@<host>:~/
~/hermes-iot-bench/bin/python ~/pi2_benchmark.py \
  --label "pi2-<version>-minimal" \
  --cli-cmd "$HOME/hermes-iot-bench/bin/hermes-iot profile show" \
  --cli-cmd "$HOME/hermes-iot-bench/bin/hermes --version" \
  --out ~/pi2-bench-<version>.json
```

Without `HERMES_HOME` + `setup` the CLI records exit 1 (no profile configured) —
the benchmark records exit codes rather than hiding them, so check them.

## Comparing a new run against a baseline

```sh
python3 scripts/pi2_benchmark.py --compare docs/pi2-benchmarks/pi2-bench-0.21.4.post1.json \
  --label "pi2-<new version>-minimal" --out ~/pi2-bench-<new version>.json
```

`--compare` prints per-metric deltas. `--max-rss-kb` turns a peak-RSS ceiling
into a non-zero exit, which is what a CI lane would gate on.

## Caveats

- Measurements are single samples on one board, so treat small differences as
  noise — but the 0.21.4.post1 pair puts the floor tighter than a blanket rule of
  thumb: two runs 30 s apart reproduced every record within 0.02 s / 4 KiB
  (~1 %), except `agent.agent_init` itself, which moved 0.18 s. Differences
  around 1 % are not evidence; re-run before calling something a regression.
- `disk_free_*` and `loadavg` capture the moment of the run; they are context,
  not benchmarks.
- Files here are de-sensitised (`/home/<user>` collapsed to `~`). Keep it that
  way: no usernames, IPs, credentials or config contents in this directory.
