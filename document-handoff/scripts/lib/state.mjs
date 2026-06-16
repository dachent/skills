import { readFile, writeFile, rename, mkdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { randomBytes } from 'node:crypto'

export const STATE_DEFAULT = {
  project: null, source_root: null, output_dir: null,
  created_at: null, resumed_at: null, provider: null,
  copy_strategy: null, phases_completed: [],
  sessions_found: [], sessions_validated: false, file_inventory: [],
  catalog_path: null, catalog_json_path: null, digests_path: null,
  synthesis_path: null, approved_sections: [], memo_path: null,
  agent_context_path: null, verification_path: null,
  verified: false, risk_flags_count: 0
}

export async function readState(statePath) {
  const raw = await readFile(statePath, 'utf8')
  return JSON.parse(raw)
}

export async function writeState(statePath, state) {
  await mkdir(dirname(statePath), { recursive: true })
  const tmp = join(dirname(statePath), `.tmp-${randomBytes(4).toString('hex')}.json`)
  await writeFile(tmp, JSON.stringify(state, null, 2), 'utf8')
  await rename(tmp, statePath)
}

export function phaseComplete(state, phase) {
  return state.phases_completed.includes(phase)
}
