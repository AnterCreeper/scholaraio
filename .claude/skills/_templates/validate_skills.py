#!/usr/bin/env python3
"""Validate all ScholarAIO skills against the HARNESS.md rules."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

SKILLS_DIR = Path(__file__).parent.parent
HARNESS_DOC = Path(__file__).parent / "HARNESS.md"

# Deprecated CLI aliases that skills should NOT use
DEPRECATED_ALIASES = {
    "--top": "use --limit instead",
}

# Known invalid CLI combinations
INVALID_COMBINATIONS = [
    (r"scholaraio diagram --from-text .* --critic", "--critic only works with paper_id, not --from-text"),
]

# Absolute path patterns that should not appear in skills
BAD_PATH_PATTERNS = [
    re.compile(r"/root/\.claude/"),
    re.compile(r"/home/\w+/"),
    re.compile(r"/tmp/[\w\-]+"),
]


def check_frontmatter(skill_path: Path) -> list[str]:
    content = skill_path.read_text(encoding="utf-8")
    issues: list[str] = []

    if not content.startswith("---"):
        issues.append("Missing YAML frontmatter")
        return issues

    end = content.find("\n---", 3)
    if end == -1:
        issues.append("Malformed frontmatter (no closing ---)")
        return issues

    try:
        fm = yaml.safe_load(content[3:end])
    except yaml.YAMLError as e:
        issues.append(f"Invalid YAML frontmatter: {e}")
        return issues

    if not isinstance(fm, dict):
        issues.append("Frontmatter is not a dict")
        return issues

    for field in ("tier", "destructive"):
        if field not in fm:
            issues.append(f"Missing frontmatter field: {field}")

    if fm.get("destructive") is True:
        body = content[end + 4 :]
        # crude heuristic: destructive skills should mention confirmation or backup
        if not any(kw in body for kw in ("确认", "confirm", "备份", "backup", "dry-run")):
            issues.append("destructive: true but no confirmation/backup/dry-run guidance found")

    return issues


def check_content(skill_path: Path) -> list[str]:
    content = skill_path.read_text(encoding="utf-8")
    issues: list[str] = []

    # 1. Deprecated aliases (word boundary to avoid matching --topic as --top)
    for alias, suggestion in DEPRECATED_ALIASES.items():
        pattern = re.compile(re.escape(alias) + r"\b")
        if pattern.search(content):
            issues.append(f"Found deprecated alias '{alias}': {suggestion}")

    # 2. Invalid CLI combinations
    for pattern, msg in INVALID_COMBINATIONS:
        if re.search(pattern, content):
            issues.append(f"Invalid CLI combination: {msg}")

    # 3. Hardcoded absolute paths
    for pat in BAD_PATH_PATTERNS:
        for m in pat.finditer(content):
            snippet = content[max(0, m.start() - 10) : m.end() + 10].replace("\n", " ")
            issues.append(f"Hardcoded absolute path: ...{snippet}...")

    # 4. Long inline subagent prompts (heuristic: more than 3 lines of quoted Chinese prompt inside skill)
    # This is a soft warning
    code_blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)
    for block in code_blocks:
        lines = block.splitlines()
        if len(lines) > 8 and "你的任务是" in block:
            issues.append("Long inline subagent prompt detected; consider moving to _templates/")

    return issues


def main() -> int:
    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        return 1

    total_issues = 0
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        name = skill_md.parent.name
        issues = check_frontmatter(skill_md) + check_content(skill_md)
        if issues:
            total_issues += len(issues)
            print(f"\n[{name}]")
            for issue in issues:
                print(f"  - {issue}")

    if total_issues == 0:
        print("All skills passed validation.")
        return 0
    else:
        print(f"\nTotal issues: {total_issues}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
