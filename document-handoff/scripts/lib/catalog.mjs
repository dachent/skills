import { readFile, stat } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { basename, relative, extname } from 'node:path'

const HIGH_RISK_NAMES = /^(\.env(\..+)?|.*private.*\.(pem|key|p12|pfx)|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|credentials?\.json|service-account\.json)$/i
const HIGH_RISK_CONTENT_MATCH = /secret/i

const CREDENTIAL_PATTERNS = [
  { re: /postgresql:\/\/[^:]+:[^@]+@/, label: 'db-connection-string' },
  { re: /(?:sk|pk)[-_][A-Za-z0-9]{20,}/, label: 'api-key' },
  { re: /password\s*[:=]\s*["']?\S{4,}/, label: 'password' },
  { re: /-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----/, label: 'private-key' }
]

const BINARY_EXTS = new Set(['.pdf','.xlsx','.xls','.docx','.doc','.zip','.tar','.gz','.png','.jpg','.jpeg','.gif','.ico','.woff','.woff2','.ttf','.exe','.dll','.bin'])

const BUCKET_MAP = {
  plans: ['.md','.txt','.rst'],
  code: ['.js','.mjs','.ts','.tsx','.py','.rb','.go','.rs','.java','.cs','.cpp','.c','.h'],
  artifacts: ['.pdf','.xlsx','.docx','.zip','.tar','.gz']
}

export async function buildEntry(filePath, sourceRoot) {
  const rel = relative(sourceRoot, filePath).replace(/\\/g, '/')
  const name = basename(filePath)
  const ext = extname(filePath).toLowerCase()
  const s = await stat(filePath)
  const isBin = BINARY_EXTS.has(ext)
  let sha256 = null
  if (!isBin && s.size < 5 * 1024 * 1024) {
    const buf = await readFile(filePath)
    sha256 = createHash('sha256').update(buf).digest('hex')
  }
  return {
    id: rel, rel_path: rel, basename: name, ext,
    size_bytes: s.size, is_binary: isBin, sha256,
    risk_flags: [], action: 'copy',
    bucket: classifyBucket(rel, ext),
    dest_rel_path: null,
    cited_in_digests: [], cited_in_sections: []
  }
}

export function scanRisks(filePath, content) {
  const flags = []
  const name = basename(filePath)
  if (HIGH_RISK_NAMES.test(name) || HIGH_RISK_CONTENT_MATCH.test(name)) {
    flags.push({ type: 'high-risk-filename', pattern: name })
  }
  for (const { re, label } of CREDENTIAL_PATTERNS) {
    if (re.test(content)) flags.push({ type: 'credential-pattern', label })
  }
  return flags
}

export function detectCollisions(entries) {
  const seen = new Set()
  for (const e of entries) {
    if (seen.has(e.basename)) return 'path-preserving'
    seen.add(e.basename)
  }
  return 'flat'
}

export function backfillCitations(catalog, digests, sectionMap) {
  for (const d of digests) {
    for (const id of (d.catalog_ids_referenced || [])) {
      const e = catalog.find(x => x.id === id)
      if (e && !e.cited_in_digests.includes(d.session_name)) e.cited_in_digests.push(d.session_name)
    }
  }
  for (const [sec, ids] of Object.entries(sectionMap)) {
    for (const id of ids) {
      const e = catalog.find(x => x.id === id)
      if (e && !e.cited_in_sections.includes(sec)) e.cited_in_sections.push(sec)
    }
  }
}

export function buildCitationIndex(catalog) {
  const idx = {}
  for (const e of catalog) {
    if (e.cited_in_digests.length || e.cited_in_sections.length) {
      idx[e.id] = { cited_in_digests: e.cited_in_digests, cited_in_sections: e.cited_in_sections }
    }
  }
  return idx
}

function classifyBucket(relPath, ext) {
  const lower = relPath.toLowerCase()
  if (lower.includes('plans/') || lower.includes('docs/')) {
    if (BUCKET_MAP.plans.includes(ext)) return 'plans'
  }
  for (const [bucket, exts] of Object.entries(BUCKET_MAP)) {
    if (exts.includes(ext)) return bucket
  }
  return 'inputs'
}
