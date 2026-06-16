# Privacy & Security Section

## When rendered

Only when state.risk_flags_count > 0. If risk_flags_count == 0 and the section is requested, render a "No risk flags detected" stub.

## Risk flag taxonomy

| type | label | Meaning |
|---|---|---|
| high-risk-filename | — | Filename matches .env, private.pem, etc. → action:"exclude" by default |
| credential-pattern | api-key | Content matches API key pattern |
| credential-pattern | password | Content matches password= pattern |
| credential-pattern | db-connection-string | postgresql:// with credentials |
| credential-pattern | possible-token | 40+ char base64 string |

## Section JSON contract

```json
{
  "id": "privacy-security",
  "title": "Privacy & Security",
  "content": "<table>...</table> listing each flagged file with risk type and action taken",
  "catalog_ids_referenced": ["list of catalog ids for flagged files"],
  "risk_flags_count": 3
}
```

## Gate behavior

During discover phase, after writing catalog.json, output to console:

```
⚠️  HIGH-RISK FILES EXCLUDED BY DEFAULT:
  .env (high-risk-filename)
  config/private.pem (high-risk-filename)

To include any of these, edit catalog.json set action:"copy", then re-run populate.
```
