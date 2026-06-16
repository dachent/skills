import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises'
import { join, basename } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'

const DIGEST_SCHEMA = {
  type: 'object',
  properties: {
    session_name: { type: 'string' },
    key_decisions: { type: 'array', items: { type: 'string' } },
    challenges: { type: 'array', items: { type: 'string' } },
    deliverables: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string' },
    catalog_ids_referenced: { type: 'array', items: { type: 'string' } }
  },
  required: ['session_name', 'key_decisions', 'challenges', 'deliverables', 'summary', 'catalog_ids_referenced']
}

export async function run(statePath, agentFn) {
  const state = await readState(statePath)
  const { output_dir: out } = state
  const tmpDir = join(out, '.handoff', 'tmp')
  const handoffDir = join(out, '.handoff')

  if (!agentFn) {
    const { agent } = await import('@anthropic-ai/claude-code')
    agentFn = (prompt, opts) => agent(prompt, opts)
  }

  let extractFiles
  try { extractFiles = (await readdir(tmpDir)).filter(f => f.endsWith('_extract.txt')) }
  catch { extractFiles = [] }

  const digests = []
  for (const f of extractFiles) {
    const content = await readFile(join(tmpDir, f), 'utf8')
    const name = basename(f, '_extract.txt')
    const prompt = `Analyze this AI session transcript and return a digest JSON.\nSession: ${name}\n\n${content.slice(0, 40000)}`
    const digest = await agentFn(prompt, { schema: DIGEST_SCHEMA })
    if (digest) digests.push({ ...digest, session_name: name })
  }

  await mkdir(handoffDir, { recursive: true })
  const digestsPath = join(handoffDir, 'digests.json')
  await writeFile(digestsPath, JSON.stringify(digests, null, 2))

  const synthesis = digests.map(d =>
    `## ${d.session_name}\n\n${d.summary}\n\n**Key Decisions:**\n${d.key_decisions.map(k => `- ${k}`).join('\n')}`
  ).join('\n\n---\n\n')
  const synthPath = join(handoffDir, 'synthesis.md')
  await writeFile(synthPath, `# Synthesis\n\n${synthesis}`)

  state.digests_path = digestsPath
  state.synthesis_path = synthPath
  state.phases_completed.push('synthesize')
  await writeState(statePath, state)
  console.log(`✓ Synthesize: ${digests.length} session digests`)
}
