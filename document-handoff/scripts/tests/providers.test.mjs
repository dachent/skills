// Run manually: node --test scripts/tests/providers.test.mjs

import { test } from 'node:test'
import assert from 'node:assert/strict'
import { join } from 'node:path'
import { mkdir, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { findCodexSessions } from '../lib/providers.mjs'

test('findCodexSessions: zero thread matches must return zero sessions, not every session on disk', async () => {
  const codexHome = join(tmpdir(), `codex-home-${process.hrtime.bigint()}`)
  await mkdir(join(codexHome, 'archived_sessions'), { recursive: true })
  // A session that belongs to a totally different project. With no sqlite
  // db present, threadIds stays empty — that must mean "no matches", not
  // "include everything found on disk".
  await writeFile(join(codexHome, 'archived_sessions', 'rollout-unrelated-project.jsonl'), '{}')

  const prevHome = process.env.CODEX_HOME
  process.env.CODEX_HOME = codexHome
  try {
    const found = await findCodexSessions('C:\\some\\unrelated\\project\\root')
    assert.equal(found.length, 0, 'must not fall back to including every Codex session on the machine')
  } finally {
    if (prevHome === undefined) delete process.env.CODEX_HOME
    else process.env.CODEX_HOME = prevHome
    await rm(codexHome, { recursive: true, force: true })
  }
})
