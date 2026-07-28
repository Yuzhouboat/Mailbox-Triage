# `update_from_main.sh` Research

## Scope

Reviewed:

- `.agents/skills/mailbox-triage/scripts/update_from_main.sh`
- `.agents/skills/mailbox-triage/SKILL.md`

## Purpose

The script safely fast-forwards the local Mailbox-Triage checkout from the
repository's `main` branch. It is deliberately fail-closed: it updates only when
the checkout identity, branch, working-tree state, GitHub SSH access, and Git
history all meet its expectations.

## Execution Flow

1. Enable unset-variable and pipeline failure checking with `set -uo pipefail`.
2. Resolve the script's own directory through `${BASH_SOURCE[0]}`.
3. Ask Git for the containing repository root.
4. Verify that `origin` is one of the accepted URLs for
   `Yuzhouboat/Mailbox-Triage`.
5. Require the current branch to be `main`.
6. Require a completely clean working tree.
7. Create a temporary file for SSH diagnostic output and register automatic
   cleanup with `trap`.
8. Probe the remote `main` branch using `git ls-remote` over SSH.
9. Classify SSH failures as authentication/configuration (`20`) or
   network/DNS (`21`).
10. Run `git pull --ff-only ... main`.

## Side Effects and Safety

- Reads local Git metadata and contacts GitHub over SSH.
- Creates one temporary diagnostic file and removes it on exit.
- Changes tracked files only in the final `git pull --ff-only`.
- Never creates merge commits, rebases, resets, stashes, overwrites local
  changes, or falls back to HTTPS.
- A dirty working tree stops the script with exit `14`.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `10` | Script is not inside a Git checkout |
| `11` | Checkout has no `origin` remote |
| `12` | `origin` is not the expected repository |
| `13` | Current branch is not `main` |
| `14` | Working tree has uncommitted or untracked changes |
| `20` | GitHub SSH authentication, host-key, or repository access problem |
| `21` | GitHub network/DNS failure or unclassified SSH connection failure |
| Git's code | Final fast-forward pull failed |

## Development Cautions

- Because `status --porcelain` includes untracked files, any new local file also
  blocks updates.
- The final pull uses the fixed SSH URL even when the configured `origin` uses
  the accepted HTTPS form.
- `set -e` is intentionally absent. Expected failures are handled explicitly,
  while the final `git pull` naturally becomes the script's exit status.
- Run the script by its resolved path or from the directory containing the
  skill's `SKILL.md`; do not assume the workspace root contains its `scripts/`
  directory.

## Summary

This is a guarded self-updater. Its central rule is: update only a known, clean
`main` checkout from the known GitHub repository, and only by fast-forwarding
over SSH.
