import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'
import { renderMemo } from '../lib/html.mjs'
import { backfillCitations, buildCitationIndex } from '../lib/catalog.mjs'

const SECTION_IDS = [
  'bootstrap','executive-summary','deliverables','current-state',
  'technical-decisions','challenges-blockers','next-steps','context-sources',
  'open-questions','dependencies','environment','testing',
  'architecture','data-flow','changelog'
]

const SECTION_SCHEMA = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    content: { type: 'string' },
    catalog_ids_referenced: { type: 'array', items: { type: 'string' } }
  },
  required: ['title', 'content', 'catalog_ids_referenced']
}

export async function run(statePath, agentFn) {
  if (!agentFn) throw new Error('render-memo requires agentFn — must be invoked via cli.mjs')
  const state = await readState(statePath)
  const { output_dir: out, project } = state

  const digests = state.digests_path
    ? JSON.parse(await readFile(state.digests_path, 'utf8'))
    : []
  const synthesis = state.synthesis_path
    ? await readFile(state.synthesis_path, 'utf8')
    : ''

  const activeSections = [...SECTION_IDS]
  if (state.risk_flags_count > 0) activeSections.push('privacy-security')

  const sectionMap = {}
  let checkpointsWritten = 0
  await Promise.all(activeSections.map(async id => {
    const prompt = buildSectionPrompt(id, synthesis, digests, state)
    const sec = await agentFn(prompt, { schema: SECTION_SCHEMA, label: `section-${id}` })
    if (sec) {
      sectionMap[id] = sec
    } else {
      checkpointsWritten++
    }
  }))

  if (checkpointsWritten > 0 && Object.keys(sectionMap).length === 0) {
    console.log(`  ℹ ${checkpointsWritten} checkpoint(s) written. Fill response JSON files then re-run render-memo.`)
    return
  }

  const catalog = state.file_inventory || []
  const sectionCitations = {}
  for (const [id, sec] of Object.entries(sectionMap)) {
    sectionCitations[id] = sec.catalog_ids_referenced || []
  }
  backfillCitations(catalog, digests, sectionCitations)
  const citationIndex = buildCitationIndex(catalog)

  const handoffDir = join(out, '.handoff')
  await mkdir(handoffDir, { recursive: true })

  const memoHtml = await renderMemo(sectionMap, state)
  const memoPath = join(out, `${project}-memo.html`)
  await writeFile(memoPath, memoHtml)

  const citationPath = join(handoffDir, `${project}-citation-index.json`)
  await writeFile(citationPath, JSON.stringify(citationIndex, null, 2))

  const agentContextPath = join(out, `${project}-agent-context.json`)
  const agentContext = {
    project,
    generated_at: new Date().toISOString(),
    section_references: Object.fromEntries(
      Object.entries(sectionMap).map(([id, sec]) => [id, {
        catalog_ids: sec.catalog_ids_referenced || [],
        summary: (sec.content || '').replace(/<[^>]+>/g, '').slice(0, 200)
      }])
    ),
    citation_index_path: citationPath
  }
  await writeFile(agentContextPath, JSON.stringify(agentContext, null, 2))

  state.memo_path = memoPath
  state.agent_context_path = agentContextPath
  state.phases_completed.push('render-memo')
  await writeState(statePath, state)
  console.log(`✓ Memo rendered: ${memoPath}`)
}

function buildSectionPrompt(id, synthesis, digests, state) {
  const ctx = synthesis.slice(0, 8000)
  const SECTION_INSTRUCTIONS = {
    'bootstrap': 'Return the #bootstrap section. Focus on: tools used, key entry points, critical commands to run. Format as structured HTML with subsections. This section enables agents to start work immediately without reading the full memo.',
    'executive-summary': 'Return a 3-5 sentence executive summary of project outcome and current state.',
    'deliverables': 'List all completed deliverables as an HTML bulleted list.',
    'current-state': 'Describe what currently exists, what works, and what is incomplete.',
    'technical-decisions': 'List key technical decisions made with rationale. Include architecture choices, tool selections, design tradeoffs.',
    'challenges-blockers': 'List obstacles, blockers, and how they were handled.',
    'next-steps': 'Provide a prioritized list of recommended next steps.',
    'context-sources': 'List sessions, files, and external resources referenced.',
    'open-questions': 'List unresolved questions and decisions.',
    'dependencies': 'List external dependencies, versions, and installation steps.',
    'environment': 'Describe how to reproduce the development environment.',
    'testing': 'Describe how to run tests, test coverage, and test strategy.',
    'architecture': 'Describe the system architecture, components, and their relationships.',
    'data-flow': 'Describe how data flows through the system.',
    'changelog': 'List what changed in this work session vs the previous state.',
    'privacy-security': `List all risk-flagged files (${state.risk_flags_count} total) with risk type and action taken. Render as an HTML table.`
  }
  const instr = SECTION_INSTRUCTIONS[id] || `Write the ${id} section.`
  return `You are writing section "${id}" for a project handoff memo.\n\n${instr}\n\nReturn JSON matching the section contract. content must be valid HTML fragment (no script/style tags).\n\nContext:\n${ctx}`
}
