import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { extractCC, extractCodex, normalizeExtract } from '../lib/providers.mjs'

const FIXTURE = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures', 'sample-project', 'logs')

test('extractCC: extracts user message from CC JSONL fixture', async () => {
  const msgs = await extractCC(join(FIXTURE, 'session-2026-01.jsonl'))
  assert.ok(msgs.length > 0)
  assert.ok(msgs.some(m => m.includes('build the feature')))
})

test('extractCodex: extracts user message from Codex JSONL fixture', async () => {
  const msgs = await extractCodex(join(FIXTURE, 'codex-session.jsonl'))
  assert.ok(msgs.length > 0)
  assert.ok(msgs.some(m => m.includes('implement the auth flow')))
})

test('both outputs: same header format from normalizeExtract', () => {
  const ccOut = normalizeExtract(['[user] hello'], 'claude-code', 'sess-a')
  const codexOut = normalizeExtract(['[user] world'], 'codex', 'sess-b')
  assert.ok(ccOut.startsWith('# Session: sess-a (claude-code)'))
  assert.ok(codexOut.startsWith('# Session: sess-b (codex)'))
})
