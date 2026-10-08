#!/usr/bin/env python3
"""Footprint and latency benchmark for the Pi2 / low-resource targets.

Written for the Raspberry Pi 2 (armv7l, 921 MiB) because "does it still fit?"
is currently answered by watching `free -h` by hand. Every number is measured
from the running interpreter, not estimated, and the output is JSON so two runs
can be compared mechanically:

    python3 scripts/pi2_benchmark.py --label pi2-0.21.5.post1
    python3 scripts/pi2_benchmark.py --json --out /tmp/pi2-bench.json
    python3 scripts/pi2_benchmark.py --compare /tmp/pi2-bench-prev.json
    python3 scripts/pi2_benchmark.py --quick                  # skip the model leg
    python3 scripts/pi2_benchmark.py --base-url http://127.0.0.1:8080/v1 \
        --model google/gemma-3-270m-it-qat-Q4_0 --turns 3
    python3 scripts/pi2_benchmark.py --max-rss-kb 180000      # gate: exit 1 if above

Stdlib only, so it runs inside the `minimal` profile venv on the device.
Exit codes: 0 measured, 1 a --max-rss-kb gate tripped, 2 usage/IO error.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

CHILD_REPORT = (
    "import json,resource,sys,time\n"
    "t0=time.perf_counter()\n"
    "import {mod}\n"
    "dt=time.perf_counter()-t0\n"
    "print(json.dumps({'import_s':dt,'peak_rss_kb':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))\n"
)


def meminfo() -> dict:
    out = {}
    try:
        with open("/proc/meminfo", encoding="ascii") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                out[key.strip()] = int(rest.strip().split()[0])  # kB
    except OSError:
        pass
    return out


def cpu_model() -> str:
    try:
        with open("/proc/cpuinfo", encoding="ascii", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return platform.processor() or "unknown"
    for key in ("model name", "Model", "Hardware", "Processor"):
        for line in text.splitlines():
            if line.lower().startswith(key.lower()):
                _, _, value = line.partition(":")
                if value.strip():
                    return value.strip()
    return platform.processor() or "unknown"


def environment() -> dict:
    mem = meminfo()
    env = {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "python": platform.python_version(),
        "python_impl": platform.python_implementation(),
        "mem_total_kb": mem.get("MemTotal"),
        "mem_available_kb": mem.get("MemAvailable"),
        "swap_total_kb": mem.get("SwapTotal"),
        "swap_free_kb": mem.get("SwapFree"),
        "loadavg": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
    }
    for label, path in (("home", os.path.expanduser("~")), ("cwd", os.getcwd()), ("tmp", tempfile.gettempdir())):
        try:
            usage = shutil.disk_usage(path)
            env[f"disk_free_{label}_kb"] = usage.free // 1024
        except OSError:
            pass
    return env


def import_cost(module: str) -> dict:
    """Import `module` in a fresh interpreter and report its own cost."""
    code = CHILD_REPORT.replace("{mod}", module)
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    wall = time.perf_counter() - t0
    if proc.returncode != 0:
        return {"module": module, "error": (proc.stderr or "").strip().splitlines()[-1:] or ["failed"]}
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"module": module, "error": "unparsable child report"}
    data.update({"module": module, "wall_s": round(wall, 3)})
    data["peak_rss_kb"] = int(data.get("peak_rss_kb", 0))
    data["import_s"] = round(float(data.get("import_s", 0.0)), 3)
    return data


CLI_WRAPPER = (
    "import json,resource,subprocess,sys,time\n"
    "t0=time.perf_counter()\n"
    "p=subprocess.run(sys.argv[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
    "dt=time.perf_counter()-t0\n"
    "print(json.dumps({'wall_s':dt,'exit_code':p.returncode,"
    "'peak_rss_kb':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}))\n"
)


def run_cli(argv: list, timeout_s: int = 300) -> dict:
    """Time a command and report *its own* peak RSS.

    The command runs inside a fresh wrapper process whose RUSAGE_CHILDREN max is
    that one child's peak — sampling /proc would miss short-lived processes, and
    reading rusage in this long-lived script would report a stale high-water mark
    from an earlier, bigger command.
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", CLI_WRAPPER, *argv],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"argv": argv, "error": str(exc)}
    wall = time.perf_counter() - t0
    try:
        inner = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"argv": argv, "wall_s": round(wall, 3), "error": (proc.stderr or "").strip()[-300:]}
    return {
        "argv": argv,
        "wall_s": round(inner["wall_s"], 3),
        "peak_rss_kb": int(inner["peak_rss_kb"]),
        "peak_rss_source": "rusage-children-of-wrapper",
        "exit_code": inner["exit_code"],
        "wrapper_overhead_s": round(wall - inner["wall_s"], 3),
    }


def model_turn(base_url: str, model: str, prompt: str, max_tokens: int, timeout: int) -> dict:
    base = base_url.rstrip("/")
    url = base + "/chat/completions" if base.endswith("/v1") else base + "/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(256 * 1024)
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"url": url, "error": str(reason)}
    wall = time.perf_counter() - t0
    try:
        obj = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return {"url": url, "wall_s": round(wall, 3), "error": "invalid JSON"}
    usage = obj.get("usage") or {}
    out = {
        "url": url,
        "model": model,
        "wall_s": round(wall, 3),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
    }
    if usage.get("completion_tokens") and wall > 0:
        out["completion_tokens_per_s"] = round(usage["completion_tokens"] / wall, 2)
    return out


def compare(current: dict, previous: dict) -> list:
    rows = []
    for section in ("environment", "imports", "cli"):
        cur, prev = current.get(section), previous.get(section)
        if isinstance(cur, dict) and isinstance(prev, dict):
            for key, value in cur.items():
                if isinstance(value, (int, float)) and isinstance(prev.get(key), (int, float)):
                    rows.append({"metric": f"{section}.{key}", "was": prev[key], "now": value,
                                 "delta": round(value - prev[key], 3)})
        elif isinstance(cur, list) and isinstance(prev, list):
            for c, p in zip(cur, prev):
                for key in ("import_s", "wall_s", "peak_rss_kb"):
                    if isinstance(c.get(key), (int, float)) and isinstance(p.get(key), (int, float)):
                        rows.append({"metric": f"{section}.{c.get('module') or c.get('argv')}.{key}",
                                     "was": p[key], "now": c[key], "delta": round(c[key] - p[key], 3)})
    return rows


def print_summary(result: dict) -> None:
    env = result["environment"]
    print(f"host        : {env['hostname']} / {env['machine']} / {env['python']}")
    print(f"cpu         : {env['cpu_model']}")
    print(f"mem total   : {env.get('mem_total_kb', 0) / 1024:.0f} MiB "
          f"(available {env.get('mem_available_kb', 0) / 1024:.0f} MiB)")
    print(f"swap free   : {env.get('swap_free_kb', 0) / 1024:.0f} MiB "
          f"of {env.get('swap_total_kb', 0) / 1024:.0f} MiB")
    print(f"disk free   : home {env.get('disk_free_home_kb', 0) / 1024 / 1024:.1f} GiB")
    print()
    print("imports (fresh interpreter each):")
    for row in result.get("imports", []):
        if row.get("error"):
            print(f"  {row['module']:<28} ERROR {row['error']}")
        else:
            print(f"  {row['module']:<28} import {row['import_s']:.2f}s  "
                  f"peak RSS {row['peak_rss_kb'] / 1024:.1f} MiB")
    print()
    print("cli:")
    for row in result.get("cli", []):
        if row.get("error"):
            print(f"  {' '.join(row['argv']):<40} ERROR {row['error']}")
        else:
            print(f"  {' '.join(row['argv']):<40} {row['wall_s']:.2f}s  "
                  f"peak RSS {row['peak_rss_kb'] / 1024:.1f} MiB "
                  f"[{row.get('peak_rss_source', '?')}] (exit {row['exit_code']})")
    if result.get("model"):
        print()
        print("model turns:")
        for row in result["model"]:
            if row.get("error"):
                print(f"  ERROR {row['error']}")
            else:
                print(f"  {row['wall_s']:.2f}s  {row.get('completion_tokens') or '?'} tokens  "
                      f"{row.get('completion_tokens_per_s') or '?'} tok/s")
    if result.get("comparison"):
        print()
        print("vs baseline:")
        for row in result["comparison"]:
            print(f"  {row['metric']:<44} {row['was']} -> {row['now']}  ({row['delta']:+})")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pi2 / low-resource footprint benchmark")
    ap.add_argument("--label", default="", help="name recorded in the JSON (e.g. pi2-0.21.5.post1)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of the summary")
    ap.add_argument("--out", default="", help="also write the JSON to this path")
    ap.add_argument("--compare", default="", help="compare against a previous JSON run")
    ap.add_argument("--quick", action="store_true", help="skip the model leg")
    ap.add_argument("--modules", default="hermes_cli.iot_cli,agent.agent_init,tools.registry",
                    help="comma-separated modules whose import cost is measured (pick real entry "
                         "points: bare `hermes_cli`/`agent` top-level imports are near-empty)")
    ap.add_argument("--cli-cmd", action="append", default=None,
                    help="command whose wall time / peak RSS is measured; repeatable "
                         "(default: 'hermes-iot profile show')")
    ap.add_argument("--base-url", default=os.environ.get("SLIM_BASE_URL", ""),
                    help="OpenAI-compatible endpoint for the model leg")
    ap.add_argument("--model", default=os.environ.get("SLIM_MODEL", ""))
    ap.add_argument("--turns", type=int, default=1)
    ap.add_argument("--prompt", default="Reply with the single word: ok")
    ap.add_argument("--max-tokens", type=int, default=32)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--max-rss-kb", type=int, default=0,
                    help="fail (exit 1) if any measured peak RSS exceeds this")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])

    result = {
        "label": args.label,
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": environment(),
        "imports": [import_cost(m.strip()) for m in args.modules.split(",") if m.strip()],
        "cli": [run_cli(cmd.split()) for cmd in (args.cli_cmd or ["hermes-iot profile show"])],
        "model": [],
    }
    if args.base_url and args.model and not args.quick:
        for _ in range(max(1, args.turns)):
            result["model"].append(model_turn(args.base_url, args.model, args.prompt,
                                              args.max_tokens, args.timeout))

    if args.compare:
        try:
            with open(args.compare, encoding="utf-8") as fh:
                result["comparison"] = compare(result, json.load(fh))
        except (OSError, ValueError) as exc:
            print(f"cannot compare against {args.compare}: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_summary(result)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, indent=2, sort_keys=True)
            fh.write("\n")
        if not args.json:
            print(f"\nwrote {args.out}")

    if args.max_rss_kb:
        peaks = [r.get("peak_rss_kb", 0) for r in result["imports"] if not r.get("error")]
        peaks += [r.get("peak_rss_kb", 0) for r in result["cli"] if not r.get("error")]
        worst = max(peaks) if peaks else 0
        if worst > args.max_rss_kb:
            print(f"\nGATE: peak RSS {worst} kB exceeds --max-rss-kb {args.max_rss_kb}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
