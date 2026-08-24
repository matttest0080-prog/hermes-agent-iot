#!/usr/bin/env bash
set -euo pipefail

tagged_sha=${1:-}
authoritative_ref=${2:-refs/remotes/origin/pi2-lite}

if [[ ! "$tagged_sha" =~ ^[0-9a-fA-F]{40}$ ]]; then
  printf 'Release ancestry gate: invalid tagged SHA: %s\n' "$tagged_sha" >&2
  exit 2
fi
if ! git rev-parse --verify --quiet "${authoritative_ref}^{commit}" >/dev/null; then
  printf 'Release ancestry gate: authoritative ref is missing: %s\n' "$authoritative_ref" >&2
  exit 2
fi
if ! git cat-file -e "${tagged_sha}^{commit}" 2>/dev/null; then
  printf 'Release ancestry gate: tagged commit is missing: %s\n' "$tagged_sha" >&2
  exit 2
fi
if ! git merge-base --is-ancestor "$tagged_sha" "$authoritative_ref"; then
  printf 'Release ancestry gate: tagged SHA %s is not an ancestor of %s\n' \
    "$tagged_sha" "$authoritative_ref" >&2
  exit 1
fi
printf 'Release ancestry gate: %s is on authoritative %s history\n' \
  "$tagged_sha" "$authoritative_ref"
