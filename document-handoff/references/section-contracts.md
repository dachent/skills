# Section Contracts

Each section agent MUST return a JSON object matching this schema. html.mjs renders it — agents must NOT return raw HTML.

## Base contract (all sections)

```json
{
  "id": "string — matches HTML id attribute (e.g. 'executive-summary')",
  "title": "string — display title",
  "content": "string — HTML fragment (p, ul, table tags allowed; no script/style)",
  "catalog_ids_referenced": ["array of catalog entry ids cited in this section"]
}
```

## Section registry (16 sections in sidebar order)

| id | title | Required | Notes |
|---|---|---|---|
| bootstrap | Quick-Start Bootstrap | yes | Structured: tools, entry points, key commands. First in sidebar. |
| executive-summary | Executive Summary | yes | 3-5 sentences on outcome and state |
| deliverables | Deliverables | yes | Bulleted list of completed artifacts |
| current-state | Current State | yes | What exists, what works, what doesn't |
| technical-decisions | Technical Decisions | yes | Key choices and rationale |
| challenges-blockers | Challenges & Blockers | yes | Obstacles encountered |
| next-steps | Next Steps | yes | Prioritized continuation list |
| context-sources | Context Sources | yes | Sessions, files referenced |
| open-questions | Open Questions | yes | Unresolved items |
| dependencies | Dependencies | yes | External dependencies and versions |
| environment | Environment & Setup | yes | Reproduce the environment |
| testing | Testing | yes | How to run tests, test coverage |
| architecture | Architecture | yes | System/component diagram or description |
| data-flow | Data Flow | yes | How data moves through the system |
| privacy-security | Privacy & Security | conditional | Required when risk_flags_count > 0 |
| changelog | Changelog | yes | What changed vs previous version |
