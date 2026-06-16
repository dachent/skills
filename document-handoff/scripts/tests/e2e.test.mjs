// ponytail: e2e calls live AI agents — exclude from CI default
// Run manually: node --test scripts/tests/e2e.test.mjs

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { rm, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { writeState, readState, STATE_DEFAULT } from '../lib/state.mjs'
import { run as discover } from '../phases/discover.mjs'
import { run as populate } from '../phases/populate.mjs'
import { run as extract } from '../phases/extract-sessions.mjs'

const FIXTURE = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures', 'sample-project')

test('e2e: discover + populate complete without error on fixture', async () => {
  const out = join(tmpdir(), `e2e-${process.hrtime.bigint()}`)
  const statePath = join(out, '.handoff', 'state.json')
  await writeState(statePath, { ...STATE_DEFAULT, project: 'e2e-test', source_root: FIXTURE, output_dir: out })
  await discover(statePath)
  await populate(statePath)
  const state = await readState(statePath)
  assert.ok(state.phases_completed.includes('discover'))
  assert.ok(state.phases_completed.includes('populate'))
  assert.ok(state.catalog_json_path)
  const catalog = JSON.parse(await readFile(state.catalog_json_path, 'utf8'))
  assert.ok(catalog.entries.length > 0, 'catalog should have entries')
  assert.equal(catalog.copy_strategy, 'path-preserving', 'fixture has collisions')
  await rm(out, { recursive: true, force: true })
})
