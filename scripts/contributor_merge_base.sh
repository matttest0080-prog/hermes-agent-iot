#!/usr/bin/env bash
# Resolve the commit range start used by the contributor-attribution workflow.
# Inputs are supplied through GitHub event-derived environment variables.
set -euo pipefail

zero_sha="0000000000000000000000000000000000000000"
pr_base_sha="${PR_BASE_SHA:-}"
push_before_sha="${PUSH_BEFORE_SHA:-}"
default_branch="${DEFAULT_BRANCH:-}"

is_sha() {
    [[ "$1" =~ ^[0-9a-f]{40}$ ]]
}

fallback_to_default_branch() {
    if [[ -z "$default_branch" ]]; then
        printf 'error: DEFAULT_BRANCH is required when no usable event base SHA exists\n' >&2
        return 1
    fi
    local remote_ref="refs/remotes/origin/${default_branch}"
    if ! git show-ref --verify --quiet "$remote_ref"; then
        printf 'error: default branch remote ref is unavailable: %s\n' "$remote_ref" >&2
        return 1
    fi
    printf '%s\n' "$remote_ref"
}

if [[ -n "$pr_base_sha" ]]; then
    if ! is_sha "$pr_base_sha"; then
        printf 'error: PR_BASE_SHA must be a 40-character lowercase hexadecimal SHA\n' >&2
        exit 1
    fi
    candidate="$pr_base_sha"
elif [[ -n "$push_before_sha" ]]; then
    if ! is_sha "$push_before_sha"; then
        printf 'error: PUSH_BEFORE_SHA must be a 40-character lowercase hexadecimal SHA\n' >&2
        exit 1
    fi
    if [[ "$push_before_sha" == "$zero_sha" ]]; then
        candidate=$(fallback_to_default_branch)
    else
        candidate="$push_before_sha"
    fi
else
    candidate=$(fallback_to_default_branch)
fi

if ! git cat-file -e "${candidate}^{commit}" 2>/dev/null; then
    printf 'error: contributor range base is not an available commit: %s\n' "$candidate" >&2
    exit 1
fi

if ! merge_base=$(git merge-base "$candidate" HEAD); then
    printf 'error: unable to determine a merge base between %s and HEAD\n' "$candidate" >&2
    exit 1
fi

printf '%s\n' "$merge_base"
