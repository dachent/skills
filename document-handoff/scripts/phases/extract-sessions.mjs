import { mkdir, writeFile, copyFile } from 'node:fs/promises'
import { join, extname } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'
import { findCCSessions, findCodexSessions, extractCC, extractCodex, normalizeExtract } from '../lib/providers.mjs'

export async function run(statePath) {
  const state = await readState(statePath)
  const { source_root: src, output_dir: out } = state

  const [ccSessions, codexSessions] = await Promise.all([
    findCCSessions(src),
    findCodexSessions(src)
  ])
  const allSessions = [...ccSessions, ...codexSessions]

  if (allSessions.length === 0) {
    console.log('⚠️  No sessions found for this source root.')
    console.log('GATE: Set sessions_validated:true in state.json manually if you want to continue without sessions.')
    return
  }

  console.log('\nSessions found:')
  allSessions.forEach((s, i) => console.log(`  ${i + 1}. [${s.provider}] ${s.session_name}`))
  console.log('\nGATE: Review sessions above. Set sessions_validated:true in state.json to proceed.')

  // Permanent, package-visible home for session material — NOT a scratch/tmp
  // directory. synthesize.mjs reads the *_extract.txt files from here, and
  // the raw log is kept alongside so the original is never the only copy.
  const sessionsDir = join(out, '.handoff', 'sessions')
  await mkdir(sessionsDir, { recursive: true })

  for (const s of allSessions) {
    const msgs = s.provider === 'claude-code' ? await extractCC(s.path) : await extractCodex(s.path)
    const normalized = normalizeExtract(msgs, s.provider, s.session_name)
    await writeFile(join(sessionsDir, `${s.session_name}_extract.txt`), normalized)
    await copyFile(s.path, join(sessionsDir, `${s.session_name}${extname(s.path)}`))
  }

  state.sessions_found = allSessions
  state.phases_completed.push('extract-sessions')
  await writeState(statePath, state)
  console.log(`✓ Extracted ${allSessions.length} sessions to ${sessionsDir}`)
}
