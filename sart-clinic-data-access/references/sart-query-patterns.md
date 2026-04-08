# SART Query Patterns

## Quick Start

Use the smallest search that can confirm the clinic and `ClinicPKID`, then switch to the exact SART page the user needs.

## Metric To Page Map

| User asks for | Use this page |
| --- | --- |
| retrieval counts | Retrieval & Transfer Tables |
| cycle volume | Retrieval & Transfer Tables |
| PGT-A utilization | Retrieval & Transfer Tables |
| embryo yield | Retrieval & Transfer Tables |
| egg freezing cycle counts | Retrieval & Transfer Tables |
| live birth rate | CSR |
| cumulative outcome | CSR |
| new patient success rate | CSR |

## PKID Lookup Queries

Primary exact-name query:

```text
site:sartcorsonline.com "CLINIC NAME"
```

Fallbacks:

```text
sartcorsonline.com "clinicwebsite.com"
sartcorsonline.com "[City] [State] fertility ClinicPKID"
site:sartcorsonline.com "[Dr. Last Name]" fertility
```

## Year-Specific Retrieval Unlock Query

When the retrieval page URL has not already appeared in search results:

```text
sartcorsonline.com ClinicPKID={ID} reportingYear={YEAR}
```

After the result is surfaced, open:

```text
https://sartcorsonline.com/EmbryoOutcome/PublicSARTOutcomeTables?ClinicPKID={ID}&reportingYear={YEAR}
```

## CSR URL

```text
https://www.sartcorsonline.com/rptCSR_PublicMultYear.aspx?ClinicPKID={ID}
```

Use this when the user wants outcome or success-rate metrics rather than volume or embryo-yield metrics.

## Worked Patterns

- "Find the SART PKID for Boston IVF in Waltham" -> exact-name query first, then use snippet address to choose the right location.
- "Get 2024 retrieval volume for clinic X" -> find PKID, search the year unlock query, then open the Retrieval & Transfer Tables page.
- "What is clinic Y's live birth rate?" -> find PKID, then open the CSR page instead of the year-specific retrieval page.
- "I can't find Boca Fertility" -> retry with domain, city/state, or medical-director fallback because the SART name may not match the marketing name exactly.
