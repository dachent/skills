export const meta = {
  name: 'handoff-synthesis',
  description: 'Extract session logs then digest all sources into synthesis',
  phases: [
    { title: 'Extract',    detail: 'Sequential batched extraction of user messages from session logs' },
    { title: 'Digest',     detail: 'Concurrent digest of extracts and doc files' },
    { title: 'Synthesize', detail: 'Write digests.json and synthesis.md' },
  ],
}

const _args = typeof args === 'string' ? JSON.parse(args) : args
const { project, source_root, output_dir, state } = _args
const { file_inventory } = state

const allFiles = (file_inventory || []).flatMap(d => d.files || [])
const extractDir = `${output_dir}\\.handoff\\tmp`

const populated = (state.phases_completed || []).includes('population')

const BUCKET_SUBDIR = {
  logs:       'logs\\claude',
  plans:      'plans',
  memory:     'memory',
  code:       'code\\src',
  artifacts:  'artifacts',
  deprecated: 'deprecated',
}

function filePath(f) {
  if (populated && f.bucket) {
    if (f.bucket === 'logs') {
      const subdir = f.rel_path.toLowerCase().includes('codex') ? 'logs\\codex' : 'logs\\claude'
      return `${output_dir}\\${subdir}\\${f.name}`
    }
    if (BUCKET_SUBDIR[f.bucket]) {
      return `${output_dir}\\${BUCKET_SUBDIR[f.bucket]}\\${f.name}`
    }
  }
  return `${source_root}\\${f.rel_path}`
}

const sessionFiles = allFiles.filter(f => f.ext === '.jsonl')

// plans\ and memory\ always read in full — critical context
const alwaysFullDocs = allFiles.filter(f =>
  ['.md', '.py', '.yaml', '.yml', '.txt', '.json'].includes(f.ext) &&
  !f.rel_path.includes('.handoff') &&
  (f.rel_path.includes('plans\\') || f.rel_path.includes('memory\\') ||
   f.bucket === 'plans' || f.bucket === 'memory')
)

// Other docs: full read, size-filtered, capped at 20 — skip inputs and deprecated
const otherDocs = allFiles.filter(f =>
  ['.md', '.py', '.yaml', '.yml', '.txt', '.json'].includes(f.ext) &&
  !f.rel_path.includes('.handoff') &&
  !f.rel_path.includes('plans\\') &&
  !f.rel_path.includes('memory\\') &&
  f.bucket !== 'plans' &&
  f.bucket !== 'memory' &&
  f.bucket !== 'inputs' &&
  f.bucket !== 'deprecated' &&
  f.bucket !== 'logs' &&
  f.size_bytes < 300000
).slice(0, 20)

const EXTRACT_SCHEMA = {
  type: 'object',
  required: ['session_name', 'written', 'message_count'],
  properties: {
    session_name:  { type: 'string' },
    written:       { type: 'boolean' },
    message_count: { type: 'number' },
  }
}

const DIGEST_SCHEMA = {
  type: 'object',
  required: ['source', 'source_type', 'key_decisions', 'challenges', 'deliverables', 'summary'],
  properties: {
    source:        { type: 'string' },
    source_type:   { type: 'string' },
    key_decisions: { type: 'array', items: { type: 'string' } },
    challenges:    { type: 'array', items: { type: 'string' } },
    deliverables:  { type: 'array', items: { type: 'string' } },
    summary:       { type: 'string' },
  }
}

phase('Extract')

// Process JSONL files in batches of 3 — never all concurrent
const EXTRACT_BATCH = 3
for (let i = 0; i < sessionFiles.length; i += EXTRACT_BATCH) {
  const batch = sessionFiles.slice(i, i + EXTRACT_BATCH)
  await parallel(batch.map(f => () =>
    agent(
      `Extract user messages from this Claude Code session log.

Input file: ${filePath(f)}
Output file: ${extractDir}\\${f.name.replace('.jsonl', '_extract.txt')}
File size: ${f.size_bytes} bytes

Instructions:
1. Read the COMPLETE input file — do not truncate or sample
2. Parse each line as JSON
3. Collect all entries where "role" is "user"
4. For each user entry, extract text content:
   - If content is a string: use it directly
   - If content is an array: join all items where type is "text", concatenating their "text" values
5. Write all extracted messages to the output file, separated by a line containing only "---"
6. Return session_name: "${f.name}", written: true, message_count: count of user messages extracted`,
      { label: `extract:${f.name}`, schema: EXTRACT_SCHEMA }
    )
  ))
  log(`Extracted ${Math.min(i + EXTRACT_BATCH, sessionFiles.length)} of ${sessionFiles.length} session logs`)
}

phase('Digest')

// Session extracts are now small — safe to run all concurrently
const sessionDigests = await parallel(sessionFiles.map(f => () =>
  agent(
    `Review this session extract and produce a structured digest.

File: ${extractDir}\\${f.name.replace('.jsonl', '_extract.txt')}
Original session: ${f.name}

Read the file. It contains user messages extracted from a Claude Code session log.

Extract:
- key_decisions: major decisions made (what was chosen and why), max 10 items
- challenges: problems encountered — prefix each with [SEEDED] if anticipated, [DISCOVERED] if unexpected. Max 10 items.
- deliverables: files or artifacts produced. Max 10 items.
- summary: 3–5 sentence narrative of what happened in this session

Return source: "${f.name}", source_type: "session_log"`,
    { label: `digest:session:${f.name}`, schema: DIGEST_SCHEMA }
  )
))

// Plans and memory — always read in full, no exceptions
const alwaysFullDigests = await parallel(alwaysFullDocs.map(f => () =>
  agent(
    `Review this critical context file and extract structured information.

File: ${filePath(f)}
File size: ${f.size_bytes} bytes

Read the COMPLETE file — do not truncate regardless of size.

Extract:
- key_decisions: important choices, patterns, or design decisions. Max 5 items.
- challenges: problems, workarounds, or known limitations. Max 5 items.
- deliverables: what this file produces or represents. Max 3 items.
- summary: 2–3 sentence description of this file's purpose.

Return source: "${f.rel_path}", source_type: "document"`,
    { label: `digest:critical:${f.name}`, schema: DIGEST_SCHEMA }
  )
))

// Other docs — full read, normal concurrency
const otherDocDigests = await parallel(otherDocs.map(f => () =>
  agent(
    `Review this file and extract structured information.

File: ${filePath(f)}
File size: ${f.size_bytes} bytes

Read the full file. Extract:
- key_decisions: important choices, patterns, or design decisions. Max 5 items.
- challenges: problems, workarounds, or known limitations. Max 5 items.
- deliverables: what this file produces or represents. Max 3 items.
- summary: 2–3 sentence description of this file's purpose.

Return source: "${f.rel_path}", source_type: "document"`,
    { label: `digest:doc:${f.name}`, schema: DIGEST_SCHEMA }
  )
))

const allDigests = [...sessionDigests, ...alwaysFullDigests, ...otherDocDigests].filter(Boolean)

phase('Synthesize')

await agent(
  `Write this JSON data exactly to file: ${output_dir}\\${project}-digests.json

${JSON.stringify(allDigests, null, 2)}`,
  { label: 'write-digests' }
)

await agent(
  `Write a synthesis document for project "${project}".

Output file: ${output_dir}\\${project}-synthesis.md

Source digests (JSON): ${JSON.stringify(allDigests)}

Write this exact markdown structure:

# ${project} — Project Synthesis

## Project Summary
[2–3 paragraph narrative: what the project accomplished, approach taken, outcome]

## Key Decisions
[Deduplicated bullet list. Format: "- Decision: <what>. Reason: <why>."]

## Challenges
[Bullet list. Format: "- [SEEDED|DISCOVERED] <description>. Resolution: <how resolved or current status>."]

## Deliverables
[Deduplicated bullet list. Format: "- <path or name>: <what it is>"]

## Sessions Overview
| Session | Type | Key Decisions | Challenges | Summary |
|---------|------|---------------|------------|---------|
[One row per digest entry]

## Gaps and Open Questions
[Things not fully resolved, areas needing deeper review, dependencies not verified]

Write the complete markdown to the output file.`,
  { label: 'write-synthesis' }
)

return {
  digests_path:   `${output_dir}\\${project}-digests.json`,
  synthesis_path: `${output_dir}\\${project}-synthesis.md`,
  digest_count:   allDigests.length,
  session_count:  sessionFiles.length,
  doc_count:      alwaysFullDocs.length + otherDocs.length,
}
