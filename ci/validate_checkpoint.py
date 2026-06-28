#!/usr/bin/env python3
"""Validate an idempotency checkpoint: schema, code-state freshness, and coverage.

This does NOT decide whether the idempotency tests pass — the workflow runs them in
a separate step. This decides whether the checkpoint is well-formed, still matches the
code it was generated against, and covers every current state-mutating source file.
If any check fails, the deploy must be blocked and the IDE audit re-run.

Usage:  python validate_checkpoint.py .idempotency-checkpoint.json
Exit:   0 = valid (allow), 1 = invalid/stale/uncovered (block), 2 = usage error

Stdlib only — safe to run in CI without installing anything.

Known limitations (intentional — documented so they don't get "fixed" by surprise):

  1. Hash-based freshness reads a content-preserving rename as "file removed."
     A handler moved from app/api.py to app/v2/api.py with identical bytes will
     block the gate ("audited file removed/renamed; re-run audit") even though
     nothing about idempotency itself has changed. This is safe (false-block beats
     false-pass) but slightly noisy. Do NOT relax this by hashing-by-content-only:
     a content-equal-but-relocated file might mean a routing change the audit
     never saw, and we'd silently miss it.

  2. `source_globs` defines the audited surface and MUST be set per-repo. The
     default in the prompt only matches one project shape (e.g., handlers under
     `app/`); other layouts need different globs. The engine's RepoProfile (design
     Step 3, field `mutatingSourceGlobs`) is the right place to derive them — the
     idempotency prompt template should be rendered with the project's actual
     globs, not a hardcoded default. A wrong glob is invisible to this validator:
     the gap shows up as "tests pass, but the gate didn't actually look at the
     new code."
"""

import hashlib
import json
import sys
from pathlib import Path

REQUIRED = {"schema_version", "constraint", "generated_against", "source_globs",
            "entry_points", "tests", "result"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(path: str) -> int:
    cp = json.loads(Path(path).read_text())

    missing = REQUIRED - cp.keys()
    if missing:
        print(f"BLOCK  checkpoint missing fields: {sorted(missing)}")
        return 1

    problems: list[str] = []

    # 1. The audit itself must have passed with nothing left uncovered.
    if cp["result"].get("status") != "pass":
        problems.append(f"audit result status is {cp['result'].get('status')!r}")
    if cp["result"].get("uncovered"):
        problems.append(f"uncovered entry points: {cp['result']['uncovered']}")

    # 2. Freshness — every audited file must still hash to its recorded value.
    recorded = {Path(f["path"]).as_posix(): f["sha256"]
                for f in cp["generated_against"]["files"]}
    for p, want in recorded.items():
        fp = Path(p)
        if not fp.exists():
            problems.append(f"audited file removed/renamed: {p} (re-run audit)")
        elif sha256(fp) != want:
            problems.append(f"audited file changed since checkpoint: {p} (re-run audit)")

    # 3. Coverage — any source file under the globs that was never audited is a gap.
    tracked = set(recorded)
    for pattern in cp["source_globs"]:
        for fp in Path(".").glob(pattern):
            if fp.is_file() and fp.as_posix() not in tracked:
                problems.append(f"new source file not covered: {fp.as_posix()} (re-run audit)")

    # 4. The named tests must exist (the workflow executes them next).
    for t in cp["tests"]:
        if not Path(t).exists():
            problems.append(f"named idempotency test missing: {t}")

    if problems:
        for m in problems:
            print(f"BLOCK  {m}")
        return 1

    print(f"PASS   checkpoint valid, fresh, and complete "
          f"({len(recorded)} files, {len(cp['entry_points'])} entry points)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: validate_checkpoint.py <checkpoint.json>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
