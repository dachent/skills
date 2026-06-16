import { copyFile, mkdir, writeFile } from 'node:fs/promises'
import { join, dirname } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'

export async function run(statePath) {
  const state = await readState(statePath)
  const { source_root: src, output_dir: out, file_inventory: entries } = state
  const refs = []

  for (const e of entries) {
    if (e.action === 'exclude') continue
    if (e.action === 'reference') { refs.push(e.rel_path); continue }
    // FIX: use dest_rel_path (not e.basename) to preserve collision strategy
    const dest = join(out, e.dest_rel_path)
    await mkdir(dirname(dest), { recursive: true })
    await copyFile(join(src, e.rel_path), dest)
  }

  if (refs.length) {
    const refsPath = join(out, 'inputs', 'REFERENCES.md')
    await mkdir(dirname(refsPath), { recursive: true })
    const content = '# Referenced Files (too large to copy)\n\n' + refs.map(r => `- ${r}`).join('\n')
    await writeFile(refsPath, content)
  }

  state.phases_completed.push('populate')
  await writeState(statePath, state)
  const copied = entries.filter(e => e.action === 'copy').length
  console.log(`✓ Populate: ${copied} files copied, ${refs.length} referenced`)
}
