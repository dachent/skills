# State Schema

state.json lives at `$output_dir/.handoff/state.json`. Written atomically (temp-swap).

## Fields

| Field | Type | Set by | Description |
|---|---|---|---|
| project | string | init | Slug name of project |
| source_root | string | init | Absolute path to source directory |
| output_dir | string | init | Absolute path to output directory |
| created_at | ISO-8601 | init | First init timestamp |
| resumed_at | ISO-8601\|null | init --resume | Resume timestamp |
| provider | string | init | 'claude-code'\|'codex'\|'unknown' |
| copy_strategy | 'flat'\|'path-preserving'\|null | discover | Set after collision detection |
| phases_completed | string[] | each phase | Phase names that completed successfully |
| sessions_found | object[] | extract | {provider,path,session_name} |
| sessions_validated | boolean | extract gate | User confirmed session list |
| file_inventory | object[] | discover | Full catalog entries array |
| catalog_path | string\|null | discover | Path to catalog.html |
| catalog_json_path | string\|null | discover | Path to catalog.json |
| digests_path | string\|null | synthesize | Path to digests.json |
| synthesis_path | string\|null | synthesize | Path to synthesis.md |
| approved_sections | string[] | sections gate | Section ids user approved |
| memo_path | string\|null | render | Path to memo.html |
| agent_context_path | string\|null | render | Path to agent-context.json |
| verification_path | string\|null | verify | Path to verification.json |
| verified | boolean | verify | True after all checks pass |
| risk_flags_count | number | discover | Count of files with risk flags |
