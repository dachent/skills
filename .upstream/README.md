# Upstream Alignment

This directory records reproducible source metadata for skills that are ports, adaptations, or source-derived local workflows.

`anthropic-skills.lock.json` pins the upstream Anthropic skills repository commit used for Office skill alignment review. Snapshot folders under `.upstream/anthropic-skills/<commit>/` are comparison baselines, not the local runtime implementation.

Policy:

- Pin upstream commits before changing skill behavior.
- Preserve upstream `LICENSE.txt` files with snapshot content.
- Treat Anthropic document skills as source-available reference material unless a separate license review says otherwise.
- Document intentional local divergence in each impacted skill's `PROVENANCE.md`.
- Make design-upskill intent explicit: provenance explains what Codex is adapting, why local Windows/Codex behavior differs, and how future no-template design improvements can be reviewed safely.
- Prefer authenticated `gh api` calls for upstream fetches and drift checks; direct GitHub HTTP requests are fallback behavior for environments without GitHub CLI.
- CI fails on invalid provenance structure or inconsistent provenance content.
- CI reports upstream drift but does not fail solely because upstream changed.
