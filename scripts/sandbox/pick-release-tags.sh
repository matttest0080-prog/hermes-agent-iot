#!/usr/bin/env bash
# Pick oldest/newest and evenly spaced supported release tags for update testing.
# Reads origin when configured, works on tagless clones, and ignores unrelated
# fork history. Offline fixture repositories without origin use reachable tags.
# Usage: pick-release-tags.sh [--count N] [--repo PATH]
set -euo pipefail

COUNT=5
REPO=
while [ "$#" -gt 0 ]; do
  case "$1" in
    --count)
      [ "$#" -ge 2 ] || { echo 'error: --count needs a value' >&2; exit 1; }
      COUNT="$2"; shift 2 ;;
    --repo)
      [ "$#" -ge 2 ] || { echo 'error: --repo needs a value' >&2; exit 1; }
      REPO="$2"; shift 2 ;;
    -h|--help) printf '%s\n' 'Usage: pick-release-tags.sh [--count N] [--repo PATH]'; exit 0 ;;
    *) echo "error: unknown argument: $1" >&2; exit 1 ;;
  esac
done
case "$COUNT" in
  ''|*[!0-9]*) echo "error: --count must be a positive integer: $COUNT" >&2; exit 1 ;;
esac
[ "$COUNT" -ge 1 ] || { echo 'error: --count must be at least 1' >&2; exit 1; }

if [ -z "$REPO" ]; then
  SOURCE="${BASH_SOURCE[0]}"
  while [ -L "$SOURCE" ]; do
    DIR="$(cd -P "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" = /* ]] || SOURCE="$DIR/$SOURCE"
  done
  script_dir="$(cd -P "$(dirname "$SOURCE")" && pwd)"
  REPO="$(git -C "$script_dir" rev-parse --show-toplevel)"
fi

# Formal upstream SemVer/CalVer and this fork's IoT/Pi2 releases only.
RELEASE_PATTERN='^(v[0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?|v[0-9]+(\.[0-9]+)+-pi2|iot-v[0-9]+\.[0-9]+\.[0-9]+(\.post[0-9]+)?)$'
remote=false
prefix="refs/hermes-release-picker/$$"
if git -C "$REPO" remote get-url origin >/dev/null 2>&1; then
  remote=true
  advertised="$(git -C "$REPO" ls-remote --refs --tags origin 'v*' 'iot-v*')"
  mapfile -t candidates < <(printf '%s\n' "$advertised" | cut -f2 | cut -c11- | grep -E "$RELEASE_PATTERN" || true)
  if [ "${#candidates[@]}" -eq 0 ]; then
    echo 'error: no supported release tags found on origin' >&2
    exit 1
  fi
  # Private refs provide tagger dates and ancestry without overwriting local
  # tags. Only picked tags are published locally; backup/canary refs never enter.
  cleanup() {
    git -C "$REPO" for-each-ref --format='delete %(refname)' "$prefix/" | git -C "$REPO" update-ref --stdin
  }
  trap cleanup EXIT
  refs=()
  for tag in "${candidates[@]}"; do refs+=("+refs/tags/$tag:$prefix/$tag"); done
  git -C "$REPO" fetch --quiet --no-tags origin "${refs[@]}"
  mapfile -t ordered < <(git -C "$REPO" for-each-ref --sort=version:refname --sort=creatordate --format='%(refname:strip=3)' "$prefix/")
else
  prefix=refs/tags
  mapfile -t ordered < <(git -C "$REPO" tag --merged HEAD --sort=version:refname --sort=creatordate --list 'v*' 'iot-v*' | grep -E "$RELEASE_PATTERN" || true)
fi

tags=()
for tag in "${ordered[@]}"; do
  if git -C "$REPO" merge-base --is-ancestor "$prefix/$tag^{commit}" HEAD; then tags+=("$tag"); fi
done
total="${#tags[@]}"
[ "$total" -gt 0 ] || { echo 'error: no reachable supported release tags found' >&2; exit 1; }

picked=()
if [ "$total" -le "$COUNT" ]; then
  picked=("${tags[@]}")
elif [ "$COUNT" -eq 1 ]; then
  picked=("${tags[$((total - 1))]}")
else
  for ((i=0; i<COUNT; i++)); do
    index=$((i * (total - 1) / (COUNT - 1)))
    picked+=("${tags[$index]}")
  done
fi
if "$remote"; then
  refs=()
  for tag in "${picked[@]}"; do refs+=("+refs/tags/$tag:refs/tags/$tag"); done
  git -C "$REPO" fetch --quiet --no-tags origin "${refs[@]}"
fi
printf '['
for i in "${!picked[@]}"; do
  [ "$i" -eq 0 ] || printf ','
  printf '"%s"' "${picked[$i]}"
done
printf ']\n'
