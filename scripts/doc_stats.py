"""Print the repository figures quoted in the documentation.

Every number in README.md and docs/AI_ASSISTED_DEVELOPMENT.md comes from here.
They are quoted with an "as of" date rather than regenerated on every commit,
because a document that churns on every push is noise in a diff -- but any
reader can re-run this and check.

This exists because those figures went stale three times during pre-publication
work. Documents that claim measured precision need a way to re-measure, or the
precision quietly becomes fiction.

Usage:
    python scripts/doc_stats.py            # human-readable
    python scripts/doc_stats.py --json     # machine-readable
    python scripts/doc_stats.py --markdown # the table used in the docs

Only tracked files are counted, so a local virtualenv or cache cannot inflate
the numbers.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# (label, path prefix, file extensions)
_LAYERS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("src/ application", "src", (".py",)),
    ("tests/", "tests", (".py",)),
    ("frontend/src/", "frontend/src", (".ts", ".tsx")),
    ("scripts/", "scripts", (".py",)),
    ("research/", "research", (".py",)),
)


def _git(*args: str) -> str:
    """Run a git command from the repository root and return stdout.

    Args:
        *args: Arguments following ``git``.

    Returns:
        Captured stdout, stripped.

    Raises:
        SystemExit: If git is unavailable or the command fails.
    """
    root = Path(__file__).resolve().parent.parent
    try:
        result = subprocess.run(
            ("git", *args), cwd=root, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"git {' '.join(args)} failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    return result.stdout.strip()


def _tracked(prefix: str, extensions: tuple[str, ...]) -> list[Path]:
    """Return tracked files under ``prefix`` with one of ``extensions``."""
    root = Path(__file__).resolve().parent.parent
    listed = _git("ls-files", prefix).splitlines()
    return [
        root / line
        for line in listed
        if line.endswith(extensions)
    ]


def _count_lines(paths: list[Path]) -> int:
    """Return the total line count across ``paths``, skipping unreadable ones."""
    total = 0
    for path in paths:
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                total += sum(1 for _ in handle)
        except OSError:
            continue
    return total


def collect() -> dict[str, object]:
    """Collect every figure quoted in the documentation.

    Returns:
        A mapping of figure name to value. Layer counts are nested under
        ``layers`` as ``{label: {"files": int, "lines": int}}``.
    """
    root = Path(__file__).resolve().parent.parent

    layers: dict[str, dict[str, int]] = {}
    for label, prefix, extensions in _LAYERS:
        paths = _tracked(prefix, extensions)
        layers[label] = {"files": len(paths), "lines": _count_lines(paths)}

    decisions_path = root / ".claude" / "DECISIONS.md"
    decisions_text = decisions_path.read_text(encoding="utf-8", errors="ignore")

    route_files = _tracked("src/api/routes", (".py",))
    endpoints = 0
    mutating = 0
    for path in route_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        endpoints += len(re.findall(r"@router\.(get|post|put|delete|patch)", text))
        mutating += len(re.findall(r"@router\.(post|put|delete|patch)", text))

    generators = len(
        [p for p in _tracked("src/core/strategy/generators", (".py",))
         if p.name != "__init__.py"]
    )
    # Indicators, excluding the scaffolding that shares the package. Counting
    # every module reported 19 and put "19 indicators" into two documents; five
    # of those are the ABC, the factory, the caching wrapper, shared helpers and
    # the timeframe resampler. None of them is an indicator, and the inflated
    # figure also dragged the quoted coverage range with it. The remaining 14
    # match the distinct classes in IndicatorFactory._registry exactly (aliases
    # excluded), which is the operational definition of "an indicator" here.
    _INDICATOR_SCAFFOLDING = {"__init__", "base", "factory", "cached", "utils", "resample"}
    indicators = len(
        [p for p in _tracked("src/core/indicators", (".py",))
         if p.stem not in _INDICATOR_SCAFFOLDING]
    )

    return {
        "layers": layers,
        "total_tracked_files": len(_git("ls-files").splitlines()),
        "commits": int(_git("rev-list", "--count", "HEAD")),
        "first_commit": _git("log", "--reverse", "--format=%ad", "--date=short").splitlines()[0],
        "last_commit": _git("log", "-1", "--format=%ad", "--date=short"),
        # The ID pattern is matched in full, not just the `### DEC-` prefix.
        # The loose form counted the `### DEC-YYYY-MM-DD-XXX: Decision Title`
        # TEMPLATE near the top of DECISIONS.md as a decision, so this script --
        # written so figures would be generated rather than typed -- reported
        # 132 where there were 131. An off-by-one in the anti-drift tool is
        # worse than an off-by-one in prose, because it is trusted.
        "decisions": len(
            re.findall(r"^### DEC-\d{4}-\d{2}-\d{2}-\d{3}:", decisions_text, re.MULTILINE)
        ),
        "decisions_lines": decisions_text.count("\n") + 1,
        "decision_ids_in_source": len(
            set(re.findall(r"DEC-20\d\d-\d\d-\d\d-\d\d\d",
                           _git("grep", "-ohE", r"DEC-20[0-9]{2}-[0-9]{2}-[0-9]{2}-[0-9]{3}",
                                "--", "src/*", "scripts/*", "research/*")))
        ),
        "api_endpoints": endpoints,
        "api_mutating_endpoints": mutating,
        "signal_generators": generators,
        "indicators": indicators,
    }


def _render_human(stats: dict[str, object]) -> str:
    """Render the figures as an aligned ASCII block."""
    layers = stats["layers"]
    assert isinstance(layers, dict)
    lines = ["Repository figures (tracked files only)", ""]
    lines.append(f"{'layer':<22}{'files':>8}{'lines':>10}")
    lines.append("-" * 40)
    for label, counts in layers.items():
        lines.append(f"{label:<22}{counts['files']:>8}{counts['lines']:>10,}")
    lines.append("-" * 40)
    lines.append("")
    for key in (
        "total_tracked_files", "commits", "first_commit", "last_commit",
        "decisions", "decisions_lines", "decision_ids_in_source",
        "api_endpoints", "api_mutating_endpoints",
        "signal_generators", "indicators",
    ):
        value = stats[key]
        rendered = f"{value:,}" if isinstance(value, int) else value
        lines.append(f"{key:<26} {rendered}")
    return "\n".join(lines)


def _render_markdown(stats: dict[str, object]) -> str:
    """Render the layer table in the form used by the documentation."""
    layers = stats["layers"]
    assert isinstance(layers, dict)
    lines = ["| Layer | Files | Lines |", "|---|---|---|"]
    for label, counts in layers.items():
        lines.append(f"| `{label}` | {counts['files']:,} | {counts['lines']:,} |")
    return "\n".join(lines)


def main() -> int:
    """Entry point.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--markdown", action="store_true", help="emit the docs table")
    args = parser.parse_args()

    stats = collect()
    if args.json:
        print(json.dumps(stats, indent=2))
    elif args.markdown:
        print(_render_markdown(stats))
    else:
        print(_render_human(stats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
