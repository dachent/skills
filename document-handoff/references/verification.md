# Verification

## 3-Stage pipeline

1. **Structural** — file existence, JSON parse, required fields present
2. **QC** — agent reads memo.html, checks coherence, coverage, accuracy
3. **Visual** — agent checks sidebar links resolve, no broken anchors, table formatting

## Additional checks

- #bootstrap section present in memo.html
- agent-context.json exists and parseable
- citation-index.json exists
- Catalog copy integrity: SHA256 of copied files matches catalog entry

## verification.json schema

```json
{
  "structural": { "passed": true, "checks": [] },
  "qc": { "passed": true, "issues": [] },
  "visual": { "passed": true, "issues": [] },
  "additional": { "bootstrap_present": true, "agent_context_exists": true, "citation_index_exists": true },
  "overall": true
}
```

## Failure criteria (any → verified:false)

1. memo.html missing
2. Any required section missing (16 sections minus privacy-security if no flags)
3. #bootstrap section missing
4. agent-context.json missing or unparseable
5. citation-index.json missing
6. QC agent returns passed:false
7. Visual agent returns passed:false
