# Security Policy

## What this software is

PARAVANT is an autonomous cryptocurrency trading system. It connects to a live
exchange and can place orders that lose money. It is published as an engineering
and research artifact, not as a product, and not as investment advice.

It is provided with no warranty of any kind. See `LICENSE`.

## Known limitations, stated deliberately

These are documented rather than hidden. If you deploy this, you are accepting
them.

### The API has no authentication

All 63 endpoints are unauthenticated, including 21 that mutate state: placing
orders, cancelling orders, closing positions, activating and deactivating the
kill switch, starting and stopping paper sessions, and changing system
configuration.

**Do not expose this API to any network you do not control.** Bind it to
localhost, or put it behind an authenticating reverse proxy or a private
network. Adding authentication is tracked in
`docs/PRODUCTION_READINESS_ASSESSMENT.md` (Phase 3, item 3.1).

### Open methodology defects in the research layer

Six known issues (PARA-03, PARA-04, PARA-05, PARA-06, PARA-07, PARA-11) remain
open and partially undercut the research layer's own conclusions. They are
severity-ranked in `docs/research/RESEARCH_FIXLIST.md`. Do not treat any
backtest result from this repository as decision-grade without reading that list
first.

### No strategy in this repository is validated

As of 2026-06-05, all eleven strategies analysed were rejected at `TIER_D` under
a Deflated Sharpe Ratio test with a conservative cost model, and two subsequent
forward hypotheses were rejected after that. See
`docs/research/retrospective/PORTFOLIO_SUMMARY_2026-06-05.md`.

Running this system with real capital means running strategies that its own
validation layer has rejected.

## Operational safety

- **The live kill switch defaults off.** Live trading requires explicitly
  setting `LIVE_TRADING_ENABLED` in the environment. It is off unless you turn
  it on.
- **Use testnet first.** `BINANCE_TESTNET=true` is the safe default. A machine
  that has run with it set to `false` is holding live-capable credentials.
- **Never commit `.env`.** It is gitignored. `.env.example` is the template.
  A scan of all commits in this repository found no credentials in history.
- **The minimum-notional guard fails closed.** If configured capital would
  produce a per-trade notional below the exchange minimum, the process exits
  rather than rounding up. Do not defeat this guard.
- **Circuit breaker state survives restart.** A tripped breaker is not reset by
  restarting the process. This is intentional.

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.

Use GitHub's private vulnerability reporting on this repository
(**Security** tab, then **Report a vulnerability**). If that is unavailable,
open an issue asking for a private contact channel without including details of
the vulnerability itself.

Please include:

- What the issue is and where in the code
- How to reproduce it
- What an attacker could achieve

This is a personal project maintained by one person. There is no service-level
commitment on response time, and there is no bounty. Reports will be
acknowledged and credited unless you ask otherwise.

## Scope

In scope:

- The application code in `src/`, `scripts/`, and `research/`
- The Dockerfile and deployment configuration
- Anything that could leak credentials or place unintended orders

Out of scope:

- The absence of API authentication, which is documented above and known
- Vulnerabilities in third-party dependencies, unless this repository uses them
  in a way that makes an otherwise-safe library unsafe
- Findings that require an attacker to already control the host
- The design prototypes under `docs/design/`
