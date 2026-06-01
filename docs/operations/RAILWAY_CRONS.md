# Railway Cron Jobs

**Last Updated:** 2026-06-01
**Audience:** Trading Operations / Deploy
**Scope:** Scheduled (cron) Railway services for the PARAVANT system.

---

## Overview

The main PARAVANT service runs continuously (`python -m scripts.run_all` — paper
trading always, live trading only when `LIVE_TRADING_ENABLED` is truthy; see
DEC-2026-05-27-001). Some tasks are not continuous — they should run on a
schedule and exit. Railway models these as **Cron Jobs**: a service with a cron
schedule whose start command runs at each tick and is expected to terminate.

This document lists every scheduled job and exactly how to configure it.

---

## Job: Daily validation report → Telegram

| Field | Value |
|-------|-------|
| **Purpose** | Passive daily visibility into per-strategy promotion classification (READY_FOR_LIVE / OBSERVING / DEGRADED / RESEARCH) so the operator can watch progression toward live re-enable without running anything by hand. |
| **Command** | `python -m scripts.validation_report --telegram` |
| **Schedule (UTC)** | `0 9 * * *` (daily at 09:00 UTC) |
| **Writes to DB?** | **No.** The report is strictly read-only (it never issues UPDATE/DELETE; the PARA-02 quarantine is a read-time filter — DEC-2026-05-31-002). Safe to run against the production Neon database. |
| **Expected runtime** | Seconds. The process prints the compact summary, sends one Telegram message, and exits 0. |

### Why a cron, not part of the main service

The classification only needs a once-a-day snapshot; running it in the main
loop would add noise and coupling. A separate scheduled service keeps it
isolated, independently observable, and trivially disabled.

### Required environment variables

Set these on the cron service (Railway dashboard → the cron service → Variables).
They mirror the main service:

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | **Yes** | Point at the **Neon** production database — that is where the real `paper_trading_sessions` live. Without it the job falls back to an empty local SQLite and reports "0 sessions". |
| `TELEGRAM_BOT_TOKEN` | Yes (for `--telegram`) | Same bot token as the main service. If unset, the job prints the summary and skips the send (no crash). |
| `TELEGRAM_CHAT_ID` | Yes (for `--telegram`) | Same chat ID as the main service. |

> Do not commit these values. They are set in the Railway service environment
> only (see `.env` locally, never checked in).

### Setup steps (one-time, Railway dashboard)

1. In the PARAVANT project, click **New** → **Empty Service** (or **+ Create** →
   service from the same repo). Name it `validation-report-cron`.
2. **Settings → Source:** use the same GitHub repo/branch as the main service so
   it builds the identical image (the `railway.toml` Dockerfile build applies).
3. **Settings → Deploy → Start Command:**
   ```
   python -m scripts.validation_report --telegram
   ```
4. **Settings → Cron Schedule:** enter
   ```
   0 9 * * *
   ```
   (Railway interprets cron schedules in **UTC**.)
5. **Settings → Variables:** add `DATABASE_URL` (Neon), `TELEGRAM_BOT_TOKEN`,
   `TELEGRAM_CHAT_ID` (copy from the main service).
6. Deploy. Railway will now run the start command at 09:00 UTC daily and mark
   the run complete when the process exits.

### Verifying

- **Manual trigger:** Railway dashboard → the cron service → **Deploy** / **Run
  Now** (or trigger a redeploy). A Telegram message should arrive within a
  minute.
- **Local dry run** (no Telegram, against local SQLite):
  ```powershell
  .venv\Scripts\python.exe -m scripts.validation_report --compact
  ```
- **Local against Neon** (read-only; sends Telegram):
  ```powershell
  $env:DATABASE_URL = '<neon_url>'
  .venv\Scripts\python.exe -m scripts.validation_report --telegram
  ```

### Interpreting the output

The summary lists each session's classification and flags PARA-02-quarantined
sessions. Promotion thresholds (DEC-2026-05-27-004):

- **READY_FOR_LIVE** — N ≥ 30 AND PF ≥ 1.35 AND Sharpe ≥ 1.0 AND MaxDD ≤ 5%
- **OBSERVING** — N ≥ 10 AND PF ≥ 1.0
- **DEGRADED** — N ≥ 10 AND PF < 0.8
- **RESEARCH** — otherwise (insufficient sample)

A strategy must reach **READY_FOR_LIVE** before the live auto-promotion gate
(DEC-2026-06-01-001) will let its tier activate.

---

## Notes

- These cron services share the same code image as the main service, so a normal
  deploy keeps them in lockstep — no separate build pipeline.
- Cron jobs do **not** trade and do **not** depend on `LIVE_TRADING_ENABLED`.
- If a job needs the persistent volume (none currently do), mount it the same way
  as the main service (`/app/data`, see `railway.toml`).
