import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { readdir } from 'node:fs/promises'
import { extractCC, extractCodex, normalizeExtract, detectProvider } from '../lib/providers.mjs'

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

test('detectProvider: CODEX_HOME env var → codex', () => {
  const orig = process.env.CODEX_HOME
  process.env.CODEX_HOME = '/custom/codex'
  try {
    assert.equal(detectProvider(), 'codex')
  } finally {
    if (orig === undefined) delete process.env.CODEX_HOME
    else process.env.CODEX_HOME = orig
  }
})

test('detectProvider: CLAUDE_SESSION_ID → claude-code', () => {
  const orig = process.env.CLAUDE_SESSION_ID
  process.env.CLAUDE_SESSION_ID = 'test-session'
  // Clear any Codex env that might interfere
  const origCodex = process.env.CODEX_HOME
  delete process.env.CODEX_HOME
  try {
    assert.equal(detectProvider(), 'claude-code')
  } finally {
    if (orig === undefined) delete process.env.CLAUDE_SESSION_ID
    else process.env.CLAUDE_SESSION_ID = orig
    if (origCodex !== undefined) process.env.CODEX_HOME = origCodex
  }
})

test('detectProvider: no env vars → unknown', () => {
  const vars = ['CLAUDE_PROJECT_PATH','CLAUDE_SESSION_ID','CODEX_SESSION_ID','CODEX_PROJECT','CODEX_HOME']
  const saved = {}
  for (const v of vars) { saved[v] = process.env[v]; delete process.env[v] }
  try {
    assert.equal(detectProvider(), 'unknown')
  } finally {
    for (const v of vars) {
      if (saved[v] !== undefined) process.env[v] = saved[v]
    }
  }
})
