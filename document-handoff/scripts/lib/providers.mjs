import { readdir, readFile } from 'node:fs/promises'
import { join, basename } from 'node:path'
import { homedir } from 'node:os'

export function detectProvider() {
  if (process.env.CLAUDE_PROJECT_PATH || process.env.CLAUDE_SESSION_ID) return 'claude-code'
  if (process.env.CODEX_SESSION_ID || process.env.CODEX_PROJECT) return 'codex'
  return 'unknown'
}

export async function findCCSessions(sourceRoot) {
  const projectsDir = join(homedir(), '.claude', 'projects')
  const found = []
  let slugDirs
  try { slugDirs = await readdir(projectsDir) } catch { return found }
  for (const slug of slugDirs) {
    const slugDir = join(projectsDir, slug)
    let files
    try { files = await readdir(slugDir) } catch { continue }
    for (const f of files) {
      if (!f.endsWith('.jsonl')) continue
      const fPath = join(slugDir, f)
      const cwd = await extractCCCwd(fPath)
      if (cwd && cwd.toLowerCase().replace(/\\/g, '/').startsWith(sourceRoot.toLowerCase().replace(/\\/g, '/'))) {
        found.push({ provider: 'claude-code', path: fPath, session_name: basename(f, '.jsonl') })
      }
    }
  }
  return found
}

async function extractCCCwd(jsonlPath) {
  try {
    const raw = await readFile(jsonlPath, 'utf8')
    for (const line of raw.split('\n').slice(0, 20)) {
      if (!line.trim()) continue
      try {
        const obj = JSON.parse(line)
        const cwd = obj.cwd || obj.message?.cwd
        if (cwd) return cwd
      } catch {}
    }
  } catch {}
  return null
}

export async function findCodexSessions(sourceRoot) {
  const archiveDir = join(homedir(), '.codex', 'archived_sessions')
  const dbPath = join(homedir(), '.codex', 'state_5.sqlite')
  const found = []
  try {
    const { DatabaseSync } = await import('node:sqlite')
    const db = new DatabaseSync(dbPath)
    const rows = db.prepare('SELECT id, cwd FROM threads WHERE cwd LIKE ?').all(`${sourceRoot}%`)
    db.close()
    const files = await readdir(archiveDir).catch(() => [])
    for (const row of rows) {
      for (const f of files) {
        if (f.includes(row.id) && f.endsWith('.jsonl')) {
          found.push({ provider: 'codex', path: join(archiveDir, f), session_name: f.replace('.jsonl', '') })
        }
      }
    }
  } catch {}
  return found
}

export async function extractCC(jsonlPath) {
  const raw = await readFile(jsonlPath, 'utf8')
  const msgs = []
  for (const line of raw.split('\n')) {
    if (!line.trim()) continue
    try {
      const obj = JSON.parse(line)
      const role = obj.message?.role || obj.type || 'unknown'
      const content = obj.message?.content ?? obj.content
      if (typeof content === 'string' && content) {
        msgs.push(`[${role}] ${content}`)
      } else if (Array.isArray(content)) {
        const text = content.filter(c => c.type === 'text').map(c => c.text).join('\n')
        if (text) msgs.push(`[${role}] ${text}`)
      }
    } catch {}
  }
  return msgs
}

export async function extractCodex(jsonlPath) {
  const raw = await readFile(jsonlPath, 'utf8')
  const msgs = []
  for (const line of raw.split('\n')) {
    if (!line.trim()) continue
    try {
      const obj = JSON.parse(line)
      if (obj.type !== 'response_item') continue
      const role = obj.payload?.role || 'unknown'
      const content = obj.payload?.content
      if (Array.isArray(content)) {
        const text = content
          .filter(c => c.type === 'input_text' || c.type === 'output_text')
          .map(c => c.text).join('\n')
        if (text) msgs.push(`[${role}] ${text}`)
      }
    } catch {}
  }
  return msgs
}

export function normalizeExtract(messages, provider, sessionName) {
  return `# Session: ${sessionName} (${provider})\n\n${messages.join('\n\n')}`
}
