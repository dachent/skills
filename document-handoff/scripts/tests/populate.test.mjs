import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { rm, stat } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { writeState, readState, STATE_DEFAULT } from '../lib/state.mjs'
import { run as discover } from '../phases/discover.mjs'
import { run as populate } from '../phases/populate.mjs'

const FIXTURE = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures', 'sample-project')

async function runBoth(outBase) {
  const out = join(tmpdir(), `ptest-${outBase}`)
  const statePath = join(out, '.handoff', 'state.json')
  await writeState(statePath, { ...STATE_DEFAULT, project: 'test', source_root: FIXTURE, output_dir: out })
  await discover(statePath)
  await populate(statePath)
  return { out, statePath }
}

test('populate: uses rel_path for path-preserving (no silent overwrite)', async () => {
  const { out, statePath } = await runBoth(process.hrtime.bigint())
  const state = await readState(statePath)
  assert.equal(state.copy_strategy, 'path-preserving')
  // Both helper.js files must exist at distinct paths
  const u = await stat(join(out, 'code', 'src', 'utils', 'helper.js')).catch(() => null)
  const c = await stat(join(out, 'code', 'src', 'components', 'helper.js')).catch(() => null)
  assert.ok(u, 'utils/helper.js not copied')
  assert.ok(c, 'components/helper.js not copied')
  await rm(out, { recursive: true, force: true })
})

test('populate: high-risk excluded files are not copied', async () => {
  const { out } = await runBoth(process.hrtime.bigint())
  const envFlat = await stat(join(out, 'inputs', '.env')).catch(() => null)
  const envPath = await stat(join(out, '.env')).catch(() => null)
  assert.equal(envFlat, null, '.env should not be copied (flat)')
  assert.equal(envPath, null, '.env should not be copied (root)')
  await rm(out, { recursive: true, force: true })
})

test('populate: marks phase complete in state', async () => {
  const { out, statePath } = await runBoth(process.hrtime.bigint())
  const state = await readState(statePath)
  assert.ok(state.phases_completed.includes('populate'))
  await rm(out, { recursive: true, force: true })
})
