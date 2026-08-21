# Security Policy

## What this software is

PARAVANT is an autonomous cryptocurrency trading system. It connects to a live
exchange and can place orders that lose money. It is published as an engineering
and research artifact, not as a product, and not as investment advice.

It is provided with no warranty of any kind. See `LICENSE`.

## Known limitations, stated deliberately

These are documented rather than hidden. If you deploy this, you are accepting
them.

### API authentication is a single shared key, and reads are not gated

As of 2026-08-14 the 19 state-mutating endpoints require a shared secret in an
`X-API-Key` header: placing orders, cancelling orders, closing positions,
activating and deactivating the kill switch, starting and stopping paper
sessions, creating and mutating strategies and accounts, and starting and
stopping the system. Set `PARAVANT_API_KEY` to enable it.

Outside `ENVIRONMENT=development` the application **refuses to start** when
`PARAVANT_API_KEY` is unset, and refuses any key shorter than 32 characters in
every environment. See `src/api/auth.py` and DEC-2026-08-14-001.

What this does **not** give you:

- **The 42 read endpoints are open.** Positions, PnL, order history, strategy
  configuration and system health are readable by anyone who can reach the
  port. This is deliberate -- the dashboard is a read-only browser client --
  but it means the API still leaks your full trading state.
- **One key, no identities.** There is no per-user attribution, no rotation
  mechanism, no expiry, and no revocation short of changing the variable and
  restarting. It authenticates a request, not a person.
- **Rate limiting is a burst cap, not a defence against a patient attacker.** As of
  2026-08-14 mutating requests are capped per client (default 30/min, keyed on
  the client-supplied `X-Forwarded-For` and therefore spoofable) and globally
  (default 120/min, un-spoofable). A leaked key can still be used indefinitely
  at 120 mutations per minute. The cap bounds the rate of damage, not the total.
  State is per process and resets on restart. See `src/api/rate_limit.py` and
  DEC-2026-08-14-003.
- **Transport is your responsibility.** The key is sent in a plaintext header.
  Over plain HTTP it is readable in transit. Terminate TLS in front of it.
- **In development with no key set, the gate is off** and logs
  `api_auth_disabled` at startup. This keeps the documented quickstart runnable.
  It also means a machine running with `ENVIRONMENT=development` on a shared
  network is fully exposed.

**Do not expose this API to any network you do not control**, even with a key
set. Bind it to localhost, or put it behind an authenticating reverse proxy or
a private network.

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
  it on. Note that the kill switch is also togglable over the API, which is why
  those endpoints are behind the key.
- **The API key gate fails closed on deployment.** Outside development, a
  missing `PARAVANT_API_KEY` aborts startup rather than serving unauthenticated
  order-placement endpoints. A crash-looping container is the intended,
  visible outcome; silent exposure is not.
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

- The limitations of the API key gate that are documented above and known: open
  read endpoints, and a single shared key with no identities or rotation
- The limits of the rate limiter that are documented above and known: per-client
  identity is spoofable via `X-Forwarded-For`, buckets are per process and reset
  on restart, and a sustained attack within the global cap is not prevented
- The development-mode bypass when `PARAVANT_API_KEY` is unset, which is
  deliberate and logged at startup
- Vulnerabilities in third-party dependencies, unless this repository uses them
  in a way that makes an otherwise-safe library unsafe
- Findings that require an attacker to already control the host
- The design prototypes under `docs/design/`
