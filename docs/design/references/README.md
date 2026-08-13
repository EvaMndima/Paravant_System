# Design references (vendored prototype)

The original visual prototype for the PARAVANT dashboard, built in Google AI
Studio and kept here as the reference the production frontend was ported from.

**This is not the application.** The frontend that ships is `frontend/`. These
files are read-only reference material: component shapes, spacing, colour usage
and interaction patterns. Nothing here is built, tested or deployed, and it is
excluded from lint and type-check.

## Why it is kept

The port was not a copy. The prototype was rebuilt onto a real design-token
system, a theme context with four palettes, path aliases and a type-checked
build, and later rebuilt again on Tailwind v3 after a v4 dark-mode failure.
Keeping the source of that port makes the difference between the two inspectable
rather than a claim.

The conventions extracted from it are written up in
[../DESIGN_GUIDE.md](../DESIGN_GUIDE.md).

## Note

This file replaces the AI Studio export's default README, which contained
generic run instructions and a link to the authoring account's private AI Studio
workspace. Neither belongs in a public repository, and neither described what
this directory is for.

Import paths in these files are relative (`../../lib/utils`); the production
frontend uses the `@/` alias.
