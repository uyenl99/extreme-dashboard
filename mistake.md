# Automation Mistakes and Preventive Actions

This file records automation failures so they are not repeated. A calculation is not considered successfully published until its output, commit, PR, checks, deployment, and task exit code are verified.

## 2026-08-18 — Incorrect preview-helper path

- Impact: The 3:00 PM pipeline stopped before running any strategy updates.
- Cause: The consolidated runner added `extreme-os-work` to the real `open_extreme_os_preview.ps1` path.
- Fix: Corrected the path in PR #23.
- Prevention: Validate every configured path from the exact Task Scheduler account and shell before disabling older tasks.

## 2026-08-18 — Timing-dependent Collective2 run discovery

- Impact: GitHub completed Collective2, but the local runner did not advance.
- Cause: The runner tried to rediscover a dispatched run by timestamp.
- Fix: Capture and poll the exact run ID returned by the dispatch.
- Prevention: Use returned IDs; never rediscover created work through timestamps or “latest” queries.

## 2026-08-18 — Windows PowerShell 5.1 incompatibility

- Impact: A polling revision worked interactively but failed under Task Scheduler.
- Cause: A `gh api --jq` expression was parsed differently by Windows PowerShell 5.1.
- Fix: Parse plain GitHub JSON with `ConvertFrom-Json`.
- Prevention: Test scheduled scripts with `powershell.exe` 5.1 and avoid complex native-command quoting.

## 2026-08-18 — GitHub read-after-write propagation delay

- Impact: The runner received a new run URL, then failed when the status endpoint was briefly unavailable.
- Fix: Retry transient status lookup failures with a bounded timeout and visible status logging.
- Prevention: All create-then-read API operations require bounded propagation retries.

## 2026-08-18 — Momentum required a clean checkout

- Impact: Mean Reversion completed, but all Momentum jobs initially stopped.
- Cause: The Web checkout was behind `origin/main` and showed already-merged scheduler edits as local modifications. ETF1 correctly refused to mix them into an automated commit.
- Fix: Synchronized to a clean `main`, then reran ETF1, ETF2, and Momentum SP.
- Prevention: Use clean disposable worktrees for publishing and verify repository cleanliness before downstream jobs.

## 2026-08-19 — Alerts succeeded but no replacement PR was created

- Impact: Alert CSVs, generated HTML, commit `2e2ee40`, and the pushed preview branch succeeded, but Task Scheduler returned `1` and no new PR opened.
- Cause: PR #17 had been merged. The script immediately attempted to create a replacement PR before GitHub fully exposed the newly pushed branch commit, and it had no retry.
- Non-cause: Two Polygon minute requests timed out and were retried. The scan completed with 512/516 minute coverage.
- Fix: Wait until the preview branch is visible ahead of `main`, retry PR discovery/creation, and log each failed attempt.
- Prevention: Publishing is incomplete until an open PR URL is recorded.

## 2026-08-19 — Generated-file staging mismatch

- Impact: A disposable checkout retained a modified `index.html` after committing the preview.
- Cause: The generator and publishing script disagreed about which generated files to stage.
- Fix: Stage the actual generator outputs and fail if `git status --porcelain` is non-empty after the automated commit.
- Prevention: Maintain one explicit generated-output list and verify a clean checkout after every automated commit.

## Required release checklist

1. Test with the exact Task Scheduler user, environment, executable, and PowerShell version.
2. Validate every path before replacing or disabling a working task.
3. Use returned IDs instead of timestamp-based rediscovery.
4. Retry API propagation delays with bounded timeouts and clear logs.
5. Use clean disposable worktrees for automated publishing.
6. Verify expected output files and timestamps after every stage.
7. Verify pushed commit, open PR, Vercel checks, production deployment, and final task exit code separately.
8. Never report success merely because calculation finished.
