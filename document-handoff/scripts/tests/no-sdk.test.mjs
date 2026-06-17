import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { mkdtemp, readFile, writeFile, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'

const PHASES_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'phases')
const LIB_DIR = join(dirname(fileURLToPath(import.meta.url)), '..', 'lib')
const toURL = p => pathToFileURL(p).href

function makeCheckpointAgentFn(checkpointDir, responses = {}) {
  return async function(prompt, opts = {}) {
    const label = (opts.label || 'item').replace(/[^a-z0-9_-]/gi, '-')
    if (responses[label] !== undefined) return responses[label]
    const schemaHint = opts.schema
      ? `\n\n---\nRequired JSON schema:\n${JSON.stringify(opts.schema, null, 2)}`
      : ''
    await writeFile(join(checkpointDir, `${label}.prompt.txt`), prompt + schemaHint)
    return null
  }
}

async function makeState(tmpOut, extra = {}) {
  const { STATE_DEFAULT, writeState } = await import(toURL(join(LIB_DIR, 'state.mjs')))
  const handoffDir = join(tmpOut, '.handoff')
  await mkdir(handoffDir, { recursive: true })
  const statePath = join(handoffDir, 'state.json')
  const state = { ...STATE_DEFAULT, project: 'no-sdk-test', output_dir: tmpOut,
    source_root: tmpOut, created_at: new Date().toISOString(), ...extra }
  await writeState(statePath, state)
  return statePath
}

test('synthesize no-sdk: writes checkpoint prompts when agentFn returns null', async () => {
  const tmpOut = await mkdtemp(join(tmpdir(), 'nosdk-synth-'))
  const handoffDir = join(tmpOut, '.handoff')
  const tmpDir = join(handoffDir, 'tmp')
  await mkdir(tmpDir, { recursive: true })
  await writeFile(join(tmpDir, 'sess1_extract.txt'), 'Session transcript content here.')

  const checkpointDir = join(handoffDir, 'checkpoints')
  await mkdir(checkpointDir, { recursive: true })
  const agentFn = makeCheckpointAgentFn(checkpointDir)

  const statePath = await makeState(tmpOut)
  const { run } = await import(toURL(join(PHASES_DIR, 'synthesize.mjs')))
  await run(statePath, agentFn)

  const promptFile = join(checkpointDir, 'session-sess1.prompt.txt')
  const content = await readFile(promptFile, 'utf8')
  assert.ok(content.includes('sess1'))
  assert.ok(content.includes('session_name')) // schema embedded
})

test('synthesize no-sdk: reads response JSON on second run', async () => {
  const tmpOut = await mkdtemp(join(tmpdir(), 'nosdk-synth2-'))
  const handoffDir = join(tmpOut, '.handoff')
  const tmpDir = join(handoffDir, 'tmp')
  const checkpointDir = join(handoffDir, 'checkpoints')
  await mkdir(tmpDir, { recursive: true })
  await mkdir(checkpointDir, { recursive: true })
  await writeFile(join(tmpDir, 'myproj_extract.txt'), 'transcript')

  const responseJson = {
    session_name: 'myproj', key_decisions: ['used node'], challenges: ['path handling'],
    deliverables: ['cli.mjs'], summary: 'Built the CLI', catalog_ids_referenced: []
  }
  await writeFile(join(checkpointDir, 'session-myproj.response.json'), JSON.stringify(responseJson))

  const agentFn = makeCheckpointAgentFn(checkpointDir, { 'session-myproj': responseJson })
  const statePath = await makeState(tmpOut)
  const { run } = await import(toURL(join(PHASES_DIR, 'synthesize.mjs')))
  await run(statePath, agentFn)

  const { readState } = await import(toURL(join(LIB_DIR, 'state.mjs')))
  const state = await readState(statePath)
  assert.ok(state.digests_path)
  const digests = JSON.parse(await readFile(state.digests_path, 'utf8'))
  assert.equal(digests.length, 1)
  assert.equal(digests[0].session_name, 'myproj')
})

test('verify no-sdk: structural checks run without agentFn, QC skipped', async () => {
  const tmpOut = await mkdtemp(join(tmpdir(), 'nosdk-verify-'))
  const handoffDir = join(tmpOut, '.handoff')
  await mkdir(handoffDir, { recursive: true })

  // Write a memo with all required sections
  const REQUIRED = ['bootstrap','executive-summary','deliverables','current-state',
    'technical-decisions','challenges-blockers','next-steps','context-sources',
    'open-questions','dependencies','environment','testing','architecture','data-flow','changelog']
  const sections = REQUIRED.map(id => `<section id="${id}"><h2>${id}</h2></section>`).join('\n')
  const memoPath = join(tmpOut, 'no-sdk-test-memo.html')
  await writeFile(memoPath, `<html><body>${sections}</body></html>`)

  const agentContextPath = join(tmpOut, 'no-sdk-test-agent-context.json')
  await writeFile(agentContextPath, '{}')
  const citationPath = join(handoffDir, 'no-sdk-test-citation-index.json')
  await writeFile(citationPath, '{}')

  const statePath = await makeState(tmpOut, { memo_path: memoPath, agent_context_path: agentContextPath })
  const { run } = await import(toURL(join(PHASES_DIR, 'verify.mjs')))
  await run(statePath, null) // no agentFn

  const { readState } = await import(toURL(join(LIB_DIR, 'state.mjs')))
  const state = await readState(statePath)
  const result = JSON.parse(await readFile(state.verification_path, 'utf8'))
  assert.ok(result.structural.passed, 'structural should pass')
  assert.ok(result.qc.skipped, 'QC should be skipped without agentFn')
  assert.ok(result.qc.passed, 'QC skipped = passed')
})
