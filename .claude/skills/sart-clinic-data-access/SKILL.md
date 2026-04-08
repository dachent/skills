---
name: sart-clinic-data-access
description: find SART ClinicPKIDs and access public SART clinic reports. use when a user needs SART data for a named fertility clinic, a specific location in a multi-site network, a reporting year, or metrics such as retrieval volume, PGT-A utilization, embryo yield, egg freezing counts, live birth rates, cumulative outcomes, or new patient success rates.
disable-model-invocation: true
---

# SART Clinic Data Access

## Notes

### Provenance

- Built from user-provided `SART Clinic Data Access Instructions.md` on April 8, 2026.
- This is an original Codex/Claude skill for navigating SART's public clinic-report workflow.

### Scope

- Use this skill for SART public clinic data lookup, not for CDC ART reports or general fertility-clinic research.
- Treat the workflow as search-first: surface a SART URL in search results before opening the exact report page.
- When year availability or report labeling could have changed, verify it in the live page before stating it as fact.

## Workflow

1. Identify the user's real target: a clinic PKID, a specific report page, or a metric.
2. Find the correct `ClinicPKID`, including the right location for multi-site brands.
3. Choose the correct SART report format for the requested metric.
4. Search for the exact SART URL in the current session before opening it.
5. If the clinic still cannot be found, tell the user it may not be a SART member and say how to verify that.

## Choose The Report

Use the Retrieval & Transfer Tables URL when the user wants:
- cycle or retrieval volumes
- PGT-A utilization
- embryo yield
- egg cryo counts
- mean embryos transferred or frozen per retrieval

Use this format:

```text
https://sartcorsonline.com/EmbryoOutcome/PublicSARTOutcomeTables?ClinicPKID={ID}&reportingYear={YEAR}
```

As of April 8, 2026, the source notes say these pages are available for `2022`, `2023`, and `2024`. Verify live availability before stating that as current fact.

Use the CSR page when the user wants:
- live birth rates
- cumulative outcomes
- new patient success rates
- intended-retrieval or transfer-based success rates

Use this format:

```text
https://www.sartcorsonline.com/rptCSR_PublicMultYear.aspx?ClinicPKID={ID}
```

The source notes say this page defaults to the most recent final year and also exposes a newer preliminary year when available. As of April 8, 2026, that note was "2023 Final" with "2024 Preliminary"; verify live labels before asserting them.

## Find The ClinicPKID

### Primary search

Start with an exact-name query:

```text
site:sartcorsonline.com "CLINIC NAME"
```

Extract `ClinicPKID=` from the result URL. For multi-location networks such as Shady Grove or CCRM, treat each PKID as a separate location and use the address snippet to match the right site.

### Fallback searches

If the exact-name query fails, the SART-registered name may differ from the clinic's marketing name. Try one or more of these:

- clinic domain: `sartcorsonline.com "clinicwebsite.com"`
- city and state: `sartcorsonline.com "[City] [State] fertility ClinicPKID"`
- medical director: `site:sartcorsonline.com "[Dr. Last Name]" fertility`

Load `sart-clinic-data-access\references\sart-query-patterns.md` for reusable search templates and worked examples.

### If the clinic still is not found

- Say that SART membership is voluntary and the clinic may not be a SART member.
- Check the clinic's own website for a SART badge or direct report link.
- Do not invent a PKID or assume a nearby location is the same clinic.

## Search-Before-Open Rule

SART pages are safest to access when the exact target URL has been surfaced in search results in the same session.

Use this sequence:

1. search for the clinic or report page first,
2. confirm the SART result contains the right `ClinicPKID`,
3. if needed, run a second search for the exact year-specific retrieval URL,
4. only then open the matching SART page.

For a year-specific retrieval page that was not already surfaced, run:

```text
sartcorsonline.com ClinicPKID={ID} reportingYear={YEAR}
```

Then open the exact Retrieval & Transfer Tables URL after it appears in results.

## Response Rules

- Name the clinic and location you matched.
- Include the `ClinicPKID` you used.
- State which report format you chose and why.
- If you mention year availability, say you verified it live or mark it as "as of April 8, 2026" from the source notes.
- If the clinic cannot be located, explain the most likely reason and the next best verification path.
