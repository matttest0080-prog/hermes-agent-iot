# gh-image deployment verification

This document records the purpose and scope of the repository's `gh-image`
verification pull request.

The pull request is intentionally documentation-only. It exercises the trusted
GitHub Actions chain without changing the Hermes Agent runtime, Raspberry Pi 2
installation profiles, or IoT behavior:

1. the pull request triggers the `CI` workflow;
2. completion of that pull-request CI triggers `Publish E2E evidence`;
3. the publisher enters the protected `gh-image` environment;
4. GitHub records the resulting environment deployment status.

The `gh-image` environment is restricted to the `pi2-lite` branch, and its
session credential is stored as the environment secret
`GH_IMAGE_SESSION_TOKEN`. The workflow installs the pinned `drogers0/gh-image`
version declared in `.github/workflows/publish-e2e-evidence.yml`.

A successful environment deployment verifies the trusted publisher job and its
credential boundary. Inline image publication additionally requires the source
CI run to produce a non-empty `e2e-evidence-*` artifact. When Desktop E2E is
temporarily disabled or produces no reviewable visual change, the publisher may
complete without uploading an image; that is distinct from a credential or
deployment failure.
