import { argv, exit } from 'node:process'

const PHASES = new Set(['init','discover','populate','extract-sessions','synthesize','render-memo','verify'])

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
await mod.run(statePath)
