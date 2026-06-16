import { readdir, readFile, writeFile, mkdir } from 'node:fs/promises'
import { join, extname } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'
import { buildEntry, scanRisks, detectCollisions } from '../lib/catalog.mjs'
import { renderCatalogHtml } from '../lib/html.mjs'

const EXCLUDE_DIRS = new Set(['node_modules','.git','.handoff','__pycache__','.next','dist','build','.venv','vendor'])
const MAX_SCAN = 300 * 1024

export async function run(statePath) {
  const state = await readState(statePath)
  const { source_root: src, output_dir: out } = state
  const entries = []
  await scanDir(src, src, entries)

  const strategy = detectCollisions(entries)
  for (const e of entries) {
    e.dest_rel_path = strategy === 'flat'
      ? `${e.bucket}/${e.basename}`
      : `${e.bucket}/${e.rel_path}`
    if (!e.is_binary && e.size_bytes < MAX_SCAN) {
      const content = await readFile(join(src, e.rel_path), 'utf8').catch(() => '')
      e.risk_flags = scanRisks(e.rel_path, content)
    }
    if (e.risk_flags.some(f => f.type === 'high-risk-filename')) e.action = 'exclude'
  }

  const catalogDir = join(out, '.handoff')
  await mkdir(catalogDir, { recursive: true })
  const catalogJsonPath = join(catalogDir, 'catalog.json')
  const catalogHtmlPath = join(catalogDir, 'catalog.html')
  await writeFile(catalogJsonPath, JSON.stringify({ entries, copy_strategy: strategy }, null, 2))
  await writeFile(catalogHtmlPath, renderCatalogHtml(entries))

  const riskCount = entries.filter(e => e.risk_flags.length).length
  const excluded = entries.filter(e => e.action === 'exclude')
  if (excluded.length) {
    console.log('\n⚠️  HIGH-RISK FILES EXCLUDED BY DEFAULT:')
    excluded.forEach(e => console.log(`  ${e.rel_path} (${e.risk_flags.map(f => f.type).join(', ')})`))
    console.log('\nEdit catalog.json to set action:"copy" on any you need, then re-run populate.')
  }

  state.copy_strategy = strategy
  state.file_inventory = entries
  state.catalog_json_path = catalogJsonPath
  state.catalog_path = catalogHtmlPath
  state.risk_flags_count = riskCount
  state.phases_completed.push('discover')
  await writeState(statePath, state)
  console.log(`\n✓ Discovery: ${entries.length} files, ${strategy} strategy, ${riskCount} risk flags`)
}

async function scanDir(dir, root, out) {
  let items
  try { items = await readdir(dir, { withFileTypes: true }) } catch { return }
  for (const item of items) {
    if (EXCLUDE_DIRS.has(item.name)) continue
    const p = join(dir, item.name)
    if (item.isDirectory()) await scanDir(p, root, out)
    else if (item.isFile()) out.push(await buildEntry(p, root))
  }
}
