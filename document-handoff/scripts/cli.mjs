import { argv, exit } from 'node:process'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { join, dirname } from 'node:path'

const PHASES = new Set(['init','discover','populate','extract-sessions','synthesize','render-memo','verify'])
const AI_PHASES = new Set(['synthesize','render-memo','verify'])

function parseArgs(args) {
  const flags = {}
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--')) {
      const key = args[i].slice(2)
      flags[key] = args[i + 1] && !args[i + 1].startsWith('--') ? args[++i] : true
    }
  }
  return flags
}

function makeNoSdkAgentFn(checkpointDir) {
  return async function noSdkAgent(prompt, opts = {}) {
    const label = (opts.label || 'item').replace(/[^a-z0-9_-]/gi, '-')
    const responseFile = join(checkpointDir, `${label}.response.json`)
    try { return JSON.parse(await readFile(responseFile, 'utf8')) } catch {}
    const schemaHint = opts.schema
      ? `\n\n---\nRequired JSON schema:\n${JSON.stringify(opts.schema, null, 2)}`
      : ''
    await writeFile(join(checkpointDir, `${label}.prompt.txt`), prompt + schemaHint)
    console.log(`  ► checkpoint: ${label}.prompt.txt`)
    return null
  }
}

async function createAgentFn(handoffDir) {
  try {
    const { agent } = await import('@anthropic-ai/claude-code')
    return (prompt, opts) => agent(prompt, opts)
  } catch {
    const checkpointDir = join(handoffDir, 'checkpoints')
    await mkdir(checkpointDir, { recursive: true })
    console.log(`  ℹ Claude Code SDK not available — checkpoint mode.`)
    console.log(`  ℹ Prompts written to: ${checkpointDir}`)
    console.log(`  ℹ Write <label>.response.json beside each prompt file, then re-run.`)
    return makeNoSdkAgentFn(checkpointDir)
  }
}

const [,, phase, ...rest] = argv
if (!phase || !PHASES.has(phase)) {
  console.error(`Unknown phase: "${phase}". Known: ${[...PHASES].join(', ')}`)
  exit(1)
}

const flags = parseArgs(rest)

if (phase === 'init') {
  const { STATE_DEFAULT, writeState, readState } = await import('./lib/state.mjs')
  const { detectProvider } = await import('./lib/providers.mjs')
  const statePath = flags.state || `${flags['output-dir'] || '.'}/.handoff/state.json`
  let state = { ...STATE_DEFAULT, project: flags.project || 'unnamed',
    source_root: flags['source-root'] || process.cwd(),
    output_dir: flags['output-dir'] || process.cwd(),
    created_at: new Date().toISOString(), provider: detectProvider() }
  if (flags.resume) {
    try {
      const ex = await readState(statePath)
      Object.assign(state, { phases_completed: ex.phases_completed, created_at: ex.created_at, resumed_at: new Date().toISOString() })
    } catch {}
  }
  await writeState(statePath, state)
  console.log(`✓ init: ${statePath}`)
  exit(0)
}

const statePath = flags.state
if (!statePath) { console.error('--state required'); exit(1) }

const mod = await import(`./phases/${phase}.mjs`)

if (AI_PHASES.has(phase)) {
  const agentFn = await createAgentFn(dirname(statePath))
  await mod.run(statePath, agentFn)
} else {
  await mod.run(statePath)
}
