import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { mkdir, rm, writeFile, readFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { readState, writeState, STATE_DEFAULT } from '../lib/state.mjs'
import { run as discover } from '../phases/discover.mjs'

const FIXTURE = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures', 'sample-project')

async function makeState(outputDir) {
  const statePath = join(outputDir, '.handoff', 'state.json')
  await writeState(statePath, { ...STATE_DEFAULT, project: 'test', source_root: FIXTURE, output_dir: outputDir })
  return statePath
}

test('discover: detects path-preserving strategy when basenames collide', async () => {
  const out = join(tmpdir(), `dtest-${process.hrtime.bigint()}`)
  const statePath = await makeState(out)
  await discover(statePath)
  const state = await readState(statePath)
  assert.equal(state.copy_strategy, 'path-preserving')
  assert.ok(state.phases_completed.includes('discover'))
  await rm(out, { recursive: true, force: true })
})

test('discover: excludes node_modules', async () => {
  const out = join(tmpdir(), `dtest-${process.hrtime.bigint()}`)
  const statePath = await makeState(out)
  await discover(statePath)
  const state = await readState(statePath)
  const hasMod = state.file_inventory.some(e => e.rel_path.includes('node_modules'))
  assert.equal(hasMod, false)
  await rm(out, { recursive: true, force: true })
})

test('discover: flags .env as high-risk and sets action:exclude', async () => {
  const out = join(tmpdir(), `dtest-${process.hrtime.bigint()}`)
  const statePath = await makeState(out)
  await discover(statePath)
  const state = await readState(statePath)
  const env = state.file_inventory.find(e => e.basename === '.env')
  assert.ok(env, '.env not found in inventory')
  assert.equal(env.action, 'exclude')
  assert.ok(env.risk_flags.some(f => f.type === 'high-risk-filename'))
  await rm(out, { recursive: true, force: true })
})

test('discover: flags config.yaml for credential pattern', async () => {
  const out = join(tmpdir(), `dtest-${process.hrtime.bigint()}`)
  const statePath = await makeState(out)
  await discover(statePath)
  const state = await readState(statePath)
  const cfg = state.file_inventory.find(e => e.basename === 'config.yaml')
  assert.ok(cfg, 'config.yaml not found')
  assert.ok(cfg.risk_flags.some(f => f.label === 'db-connection-string'))
  await rm(out, { recursive: true, force: true })
})

test('discover: writes catalog.json', async () => {
  const out = join(tmpdir(), `dtest-${process.hrtime.bigint()}`)
  const statePath = await makeState(out)
  await discover(statePath)
  const state = await readState(statePath)
  assert.ok(state.catalog_json_path)
  const catalog = JSON.parse(await readFile(state.catalog_json_path, 'utf8'))
  assert.ok(Array.isArray(catalog.entries))
  await rm(out, { recursive: true, force: true })
})
