# Hermes Agent IoT 0.23.1 release record

## Published artifact

- Package: [`hermes-agent-iot 0.23.1`](https://pypi.org/project/hermes-agent-iot/0.23.1/).
- Annotated tag: [`iot-v0.23.1`](https://github.com/matttest0080-prog/hermes-agent-iot/tree/iot-v0.23.1), targeting merge commit `5693c5a4ff0ab2158c5e2973bd2d7c40ae1a20c5` (PR #61).
- Tag publisher: [GitHub Actions run 43794424621](https://github.com/matttest0080-prog/hermes-agent-iot/actions/runs/43794424621), succeeded on 2026-11-16.
- Published file: `hermes_agent_iot-0.23.1-py3-none-any.whl` (wheel-only; no sdist).
- PyPI upload time: `2026-11-16T02:55:10.733505Z`.
- SHA-256: `ad2516e3b3eddc39e04bc7324a317be6f4f8520c8313140850520079b8729df9`. An anonymous PyPI download matched the digest returned by PyPI's version API.

The tag run verified ancestry, passed the release-focused suite (11 files, 104 tests), built and sanitized the wheel, passed Twine validation and the clean-wheel smoke test, then published through the protected `pypi` environment.

## Raspberry Pi 2 validation scope

On 2026-11-16, a locally built, sanitized `0.23.1` candidate wheel was tested on a physical Raspberry Pi 2 Model B Rev 1.1 (`armv7l`, 32-bit, 921 MiB RAM, Raspbian 13 Trixie, Python 3.13.5). That pre-release wheel was built from version-bump commit `22678bc6d5175d0e8a59853ef2f4e940c3abb8ba`, before the later documentation commit and release merge. Its SHA-256 was `a54c171f419ee41c5215d0a2be9dcbcdf9a9cc6e50891cfe5f6ab7f153dac33a`; it is **not** the published PyPI wheel above.

The test used a fresh isolated venv and `HERMES_HOME`, installed dependencies from `requirements/pi2/minimal.lock` with hashes, then installed the candidate wheel with `--no-deps`. The installed metadata reported `0.23.1`; `direct_url.json` matched the candidate wheel hash. `pip check`, core CLI imports, `hermes --help`, and `hermes_cli.iot_cli setup --profile minimal` passed. Test artifacts were removed afterwards.

This verifies a pre-release wheel candidate and the `minimal` profile setup on Pi 2. The final PyPI wheel passed the release CI clean-install smoke, but the exact published wheel was not installed on the Pi. No model request or gateway run was performed; this does not validate a model round-trip or other profiles. See the [detailed Pi 2 record](../README_PI2.md#pre-release-wheel-candidate-hardware-test-0231-2026-11-16).
