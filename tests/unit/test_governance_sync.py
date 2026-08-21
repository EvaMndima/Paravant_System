"""Mechanical enforcement of the governance rules that were previously prose.

`.claude/rules/decision-consistency.md` Rule 0 and
`.claude/rules/documentation-freshness.md` Rule 4 both require the `.claude/`
and `.agent/` trees to stay in step, so that different AI tools read identical
instructions. Until now that requirement was a checklist item, which is to say
it depended on someone remembering.

It failed at least twice while unenforced:

- `.agent/rules/mvp-scope-control.md` was missing the DEC-2026-05-28-001
  market-type amendment that `.claude/` carried, so non-Claude agents were
  reading a scope rule forbidding futures backtesting that had been permitted
  since 2026-05-28.
- The `DECISIONS.md` footer claimed 107 decisions while the file held 125.

A test is the only form of this rule that cannot be forgotten.

Decision: DEC-2026-08-14-002 - Documentation freshness is part of the change
Decision: DEC-2026-08-14-003 - Rate limiting configuration
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

CLAUDE_DIR = REPO_ROOT / ".claude"
AGENT_DIR = REPO_ROOT / ".agent"

# Read as text so Windows CRLF and Unix LF compare equal. The requirement is
# identical content, not identical bytes on disk.
_READ_KWARGS = {"encoding": "utf-8"}


def _rule_files(directory: Path) -> dict[str, Path]:
    """Map rule filename to path for one governance directory."""
    rules_dir = directory / "rules"
    return {p.name: p for p in sorted(rules_dir.glob("*.md"))}


class TestDecisionLogSync:
    """`.claude/DECISIONS.md` and `.agent/DECISIONS.md` must not diverge."""

    def test_both_decision_logs_exist(self):
        assert (CLAUDE_DIR / "DECISIONS.md").is_file()
        assert (AGENT_DIR / "DECISIONS.md").is_file()

    def test_decision_logs_are_identical(self):
        claude = (CLAUDE_DIR / "DECISIONS.md").read_text(**_READ_KWARGS)
        agent = (AGENT_DIR / "DECISIONS.md").read_text(**_READ_KWARGS)

        assert claude == agent, (
            "`.claude/DECISIONS.md` and `.agent/DECISIONS.md` have diverged. "
            "Both must be updated together -- see decision-consistency.md Rule 0. "
            "Fix with: cp .claude/DECISIONS.md .agent/DECISIONS.md"
        )

    def test_decision_ids_are_unique(self):
        """A duplicated ID makes every cross-reference to it ambiguous.

        Two duplicates predate this test. Each appears in two separate
        transcriptions that agree on substance, but the later copies cite paths
        that no longer exist (`src/paper/engine.py` rather than
        `src/core/strategy/paper/`). They are allowlisted rather than deleted
        because choosing which copy is canonical is an owner decision about a
        governance artifact, not a mechanical fix.

        The allowlist is deliberately a fixed set, not a count: it still fails
        on any NEW duplicate, which is the regression this guards against.
        Removing an entry from it once resolved is the intended direction.
        """
        text = (CLAUDE_DIR / "DECISIONS.md").read_text(**_READ_KWARGS)
        ids = re.findall(r"^### (DEC-\d{4}-\d{2}-\d{2}-\d{3}):", text, re.MULTILINE)

        known_duplicates = {"DEC-2026-02-15-001", "DEC-2026-02-15-002"}
        duplicates = {i for i in ids if ids.count(i) > 1}

        assert not (duplicates - known_duplicates), (
            f"new duplicate decision IDs: {sorted(duplicates - known_duplicates)}"
        )

    def test_known_duplicate_allowlist_has_not_gone_stale(self):
        """If a duplicate gets resolved, the allowlist entry must be removed --
        otherwise it silently masks a future recurrence of the same ID."""
        text = (CLAUDE_DIR / "DECISIONS.md").read_text(**_READ_KWARGS)
        ids = re.findall(r"^### (DEC-\d{4}-\d{2}-\d{2}-\d{3}):", text, re.MULTILINE)

        known_duplicates = {"DEC-2026-02-15-001", "DEC-2026-02-15-002"}
        still_duplicated = {i for i in ids if ids.count(i) > 1}

        resolved = known_duplicates - still_duplicated

        assert not resolved, (
            f"these IDs are no longer duplicated and must be removed from the "
            f"allowlist in this test: {sorted(resolved)}"
        )

    def test_footer_decision_count_matches_reality(self):
        """The footer count is a claim. DEC-2026-08-14-002 Rule 1.3: a number in
        a document is an assertion, and it had already drifted by 18."""
        text = (CLAUDE_DIR / "DECISIONS.md").read_text(**_READ_KWARGS)

        actual = len(
            re.findall(r"^### DEC-\d{4}-\d{2}-\d{2}-\d{3}:", text, re.MULTILINE)
        )
        claimed = re.findall(r"\*\*Total Decisions:\*\*\s*(\d+)\s*active", text)

        assert claimed, "no '**Total Decisions:** N active' footer found"
        assert int(claimed[-1]) == actual, (
            f"footer claims {claimed[-1]} active decisions, file contains {actual}"
        )


class TestRuleFileSync:
    """`.claude/rules/` and `.agent/rules/` must hold the same rules."""

    def test_same_rule_files_exist_in_both(self):
        claude_names = set(_rule_files(CLAUDE_DIR))
        agent_names = set(_rule_files(AGENT_DIR))

        assert claude_names == agent_names, (
            f"only in .claude: {sorted(claude_names - agent_names)}; "
            f"only in .agent: {sorted(agent_names - claude_names)}"
        )

    @pytest.mark.parametrize(
        "filename",
        sorted(_rule_files(CLAUDE_DIR)),
    )
    def test_rule_file_contents_match(self, filename):
        claude = (CLAUDE_DIR / "rules" / filename).read_text(**_READ_KWARGS)
        agent = (AGENT_DIR / "rules" / filename).read_text(**_READ_KWARGS)

        assert claude == agent, (
            f"`.claude/rules/{filename}` and `.agent/rules/{filename}` have "
            f"diverged. Fix with: cp .claude/rules/{filename} "
            f".agent/rules/{filename}"
        )

    def test_documentation_freshness_rule_is_present(self):
        """The rule added by DEC-2026-08-14-002 must not be quietly dropped."""
        assert "documentation-freshness.md" in _rule_files(CLAUDE_DIR)


class TestInstructionFileParity:
    """`CLAUDE.md` and `SYSTEM.md` differ by tool-specific framing, so they are
    not compared byte for byte. The substantive sections must both be present."""

    @pytest.mark.parametrize(
        "heading",
        [
            "## 1. DECISION CONSISTENCY (MANDATORY)",
            "### 4A. DOCUMENTATION FRESHNESS (MANDATORY)",
            "## 14. Post-Implementation Checklist",
        ],
    )
    def test_both_instruction_files_carry_the_section(self, heading):
        claude = (CLAUDE_DIR / "CLAUDE.md").read_text(**_READ_KWARGS)
        agent = (AGENT_DIR / "SYSTEM.md").read_text(**_READ_KWARGS)

        assert heading in claude, f"missing from .claude/CLAUDE.md: {heading}"
        assert heading in agent, f"missing from .agent/SYSTEM.md: {heading}"


class TestConfigurationIsDocumented:
    """Every environment variable the API reads must appear in `.env.example`.

    This is the mechanical half of documentation-freshness Rule 1.2: adding a
    config key without documenting it is the most common way a deployment guide
    goes stale, and it is the one case a test can catch outright.
    """

    @staticmethod
    def _env_example() -> str:
        return (REPO_ROOT / ".env.example").read_text(**_READ_KWARGS)

    def test_env_example_exists(self):
        assert (REPO_ROOT / ".env.example").is_file()

    @pytest.mark.parametrize(
        "env_var",
        [
            "PARAVANT_API_KEY",
            "API_RATE_LIMIT_PER_MINUTE",
            "API_RATE_LIMIT_GLOBAL_PER_MINUTE",
        ],
    )
    def test_variable_is_documented(self, env_var):
        assert env_var in self._env_example(), (
            f"{env_var} is read by the application but absent from .env.example"
        )

    def test_documented_names_match_the_constants(self):
        """Guards against the code and the template drifting apart via a rename
        -- the string in `.env.example` must be the string the code reads."""
        from src.api.auth import API_KEY_ENV_VAR
        from src.api.rate_limit import GLOBAL_LIMIT_ENV, PER_CLIENT_LIMIT_ENV

        template = self._env_example()

        for constant in (API_KEY_ENV_VAR, PER_CLIENT_LIMIT_ENV, GLOBAL_LIMIT_ENV):
            assert constant in template, f"{constant} missing from .env.example"

    def test_real_env_file_is_not_tracked(self):
        """`.env` holds live credentials. Tracking it would publish them."""
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", ".env"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0, ".env is tracked by git -- it must not be"


class TestSecurityDocumentationIsCurrent:
    """`SECURITY.md` is the document a deployer acts on, so a stale claim there
    is the most consequential kind. These assert the claims match the code."""

    @staticmethod
    def _security_md() -> str:
        return (REPO_ROOT / "SECURITY.md").read_text(**_READ_KWARGS)

    def test_does_not_claim_the_api_is_unauthenticated(self):
        """The pre-DEC-2026-08-14-001 claim. It was true; it no longer is."""
        text = self._security_md().lower()

        assert "all 63 endpoints are unauthenticated" not in text

    def test_documents_the_api_key(self):
        assert "PARAVANT_API_KEY" in self._security_md()

    def test_still_discloses_remaining_gaps(self):
        """documentation-freshness Rule 7: never weaken a warning without
        replacing it. Open reads and the single shared key are still real."""
        text = self._security_md().lower()

        assert "read endpoints are open" in text
        assert "rotation" in text
