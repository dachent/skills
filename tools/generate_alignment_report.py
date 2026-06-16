from __future__ import annotations

import argparse
import json
from pathlib import Path


def count_changes(change_set: dict[str, list[str]]) -> int:
    return sum(len(value) for value in change_set.values())


def render_change_list(title: str, change_set: dict[str, list[str]]) -> list[str]:
    lines = [f"### {title}", ""]
    if count_changes(change_set) == 0:
        lines.append("No file-level changes detected.")
        lines.append("")
        return lines
    for key in ("added", "removed", "changed"):
        values = change_set.get(key, [])
        if not values:
            continue
        lines.append(f"- {key}: {len(values)}")
        for value in values[:25]:
            lines.append(f"  - `{value}`")
        if len(values) > 25:
            lines.append(f"  - ... {len(values) - 25} more")
    lines.append("")
    return lines


def render(report: dict) -> str:
    lines = [
        "# Upstream Alignment Report",
        "",
        f"- Pinned upstream commit: `{report['pinned_upstream_commit']}`",
        f"- Current upstream commit: `{report['current_upstream_commit']}`",
        f"- Upstream changed: `{str(report['upstream_changed']).lower()}`",
        "",
        "## Skills",
        "",
        "| Skill | Source | Upstream path | Snapshot | Provenance | Upstream diff | Local diff | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for skill in report["skills"]:
        lines.append(
            "| {name} | {source} | `{upstream_path}` | {snapshot} | {provenance} | {upstream_diff} | {local_diff} | `{status}` |".format(
                name=skill["name"],
                source=skill["source"],
                upstream_path=skill["upstream_path"],
                snapshot="yes" if skill["snapshot_present"] else "no",
                provenance="yes" if skill["provenance_present"] else "no",
                upstream_diff=count_changes(skill["upstream_changes_since_pin"]),
                local_diff=count_changes(skill["local_vs_snapshot"]),
                status=skill["status"],
            )
        )
    lines.append("")

    for skill in report["skills"]:
        lines.append(f"## {skill['name']}")
        lines.append("")
        lines.extend(render_change_list("Upstream Changes Since Pin", skill["upstream_changes_since_pin"]))
        lines.extend(render_change_list("Local Folder Compared To Pinned Snapshot", skill["local_vs_snapshot"]))

    lines.append("## Policy")
    lines.append("")
    lines.append("Invalid provenance fails validation. Upstream drift and local adaptation drift are review signals until the repository adopts a stricter policy.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    parser.add_argument("--markdown", required=True)
    args = parser.parse_args(argv)

    report = json.loads(Path(args.json).read_text(encoding="utf-8"))
    output = Path(args.markdown)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(report), encoding="utf-8")
    print(f"Wrote alignment report to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
