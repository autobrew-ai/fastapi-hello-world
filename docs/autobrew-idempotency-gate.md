# Autobrew: idempotency gate

This PR was opened by Autobrew to install the **idempotency** deployment gate
before your service is deployed with more than one replica. Autobrew waits for
this PR to merge before enabling Railway's "Wait for CI" and triggering the first
deploy — merging it is what unblocks the deploy.

## What it installs
- `.github/workflows/idempotency-gate.yml` — runs on pushes/PRs to the deploy
  branch and **blocks** the deploy if the gate fails.
- `ci/validate_checkpoint.py` — validates the `.idempotency-checkpoint.json` checkpoint
  (integrity + freshness + coverage) and runs the recorded tests.

## The audited surface
This project's state-mutating handlers live under these globs (derived from your
repo by Autobrew — Step 3 `mutatingSourceGlobs`). Set `source_globs` in
`.idempotency-checkpoint.json` to exactly this list so the gate covers the right files:

```json
[
  "app/**/*.py"
]
```

## Recommended (Autobrew does NOT change this for you)
Mark the **idempotency-gate** workflow as a **required status check** in your
branch protection rules, so the gate cannot be bypassed by merging around it.
