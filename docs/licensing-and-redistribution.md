# Licensing and redistribution

This repository is a **mixed-license collection**. No single root license can override the terms attached to imported or derivative material.

## Repository-owned original material

Files classified as `repo-owned-original` are currently **all rights reserved** unless a file or directory contains a separate license notice. Public source access is not a grant to copy, modify, or redistribute those files. A future root license may grant broader rights only for material owned by this repository's copyright holder.

## External derivatives

The authoritative mapping is `.provenance/source-registry.json`.

- Matt Pocock skill derivatives and UltraPlan derivatives are distributed under their upstream MIT licenses. Copies of the reviewed license texts are retained in `.upstream/licenses/`.
- Anthropic-derived Office skills are governed by the license and notice files applicable to each upstream skill snapshot. The repository does not assume an Anthropic repository-wide license.
- `deep_planning.txt` derivatives and `document-handoff` have unresolved original-source licensing. They are marked `restricted` and should not be redistributed outside this repository until the source owner and license are documented.

## Boundaries

A downstream user must evaluate each skill independently. The repository's original modifications do not remove upstream attribution, notice, source-availability, or redistribution obligations. Generated catalogs summarize provenance but do not replace source license files.

## Review process

Every supported skill must have a provenance record containing classification, immutable source revision where applicable, source path, retrieval date, license review, port depth, intentional divergence, owner, and last alignment review. `tools/validate_provenance.py` enforces this inventory. Scheduled drift checks compare every registered GitHub source and identify the local skills affected by upstream changes.
