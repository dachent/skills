import { readdir, readFile, stat } from 'node:fs/promises'
import { join, basename } from 'node:path'
import { homedir } from 'node:os'

export function detectProvider() {
  if (process.env.CLAUDE_PROJECT_PATH || process.env.CLAUDE_SESSION_ID) return 'claude-code'
  if (process.env.CODEX_SESSION_ID || process.env.CODEX_PROJECT || process.env.CODEX_HOME) return 'codex'
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
      if (cwd && normPath(cwd).startsWith(normPath(sourceRoot))) {
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

// Strip Windows extended-path prefix and normalise separators + case for comparison
function normPath(p) {
  return p.replace(/^\\\\\?\\/, '').toLowerCase().replace(/\\/g, '/')
}

export async function findCodexSessions(sourceRoot) {
  const codexHome = process.env.CODEX_HOME || join(homedir(), '.codex')
  const found = []
  const normRoot = normPath(sourceRoot)

  // Find newest state_*.sqlite
  let dbPath = null
  try {
    const files = await readdir(codexHome)
    const dbs = files.filter(f => /^state_\d+\.sqlite$/.test(f))
    if (dbs.length) {
      const withMtime = await Promise.all(
        dbs.map(async f => ({ f, mtime: (await stat(join(codexHome, f))).mtimeMs }))
      )
      withMtime.sort((a, b) => b.mtime - a.mtime)
      dbPath = join(codexHome, withMtime[0].f)
    }
  } catch {}

  const threadIds = new Set()
  const rolloutPaths = new Map() // thread id -> rollout_path

  if (dbPath) {
    try {
      const { DatabaseSync } = await import('node:sqlite')
      const db = new DatabaseSync(dbPath)
      let rows
      try {
        rows = db.prepare('SELECT id, cwd, rollout_path FROM threads').all()
      } catch {
        // Older schema without rollout_path
        rows = db.prepare('SELECT id, cwd FROM threads').all()
      }
      db.close()
      for (const row of rows) {
        if (row.cwd && normPath(row.cwd).startsWith(normRoot)) {
          threadIds.add(row.id)
          if (row.rollout_path) rolloutPaths.set(row.id, row.rollout_path)
        }
      }
    } catch {}
  }

  // Scan both archived_sessions/ and sessions/ directories
  const sessionDirs = [
    join(codexHome, 'archived_sessions'),
    join(codexHome, 'sessions')
  ]

  for (const sessionDir of sessionDirs) {
    let files
    try { files = await readdir(sessionDir) } catch { continue }
    for (const f of files) {
      if (!f.endsWith('.jsonl')) continue
      // Only include files whose thread id was confirmed to match sourceRoot.
      // threadIds.size === 0 must mean "no matches", never "include everything".
      const matchesThread = [...threadIds].some(id => f.includes(id))
      if (matchesThread) {
        const fPath = join(sessionDir, f)
        if (!found.some(x => x.path === fPath)) {
          found.push({ provider: 'codex', path: fPath, session_name: f.replace('.jsonl', '') })
        }
      }
    }
  }

  // Add rollout_path entries that weren't already found via directory scan
  for (const [, rPath] of rolloutPaths) {
    if (!found.some(x => x.path === rPath)) {
      found.push({ provider: 'codex', path: rPath, session_name: basename(rPath, '.jsonl') })
    }
  }

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
