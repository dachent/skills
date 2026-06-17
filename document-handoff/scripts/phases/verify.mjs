import { readFile, writeFile, mkdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { readState, writeState } from '../lib/state.mjs'
import { createHash } from 'node:crypto'

const CHECK_SCHEMA = {
  type: 'object',
  properties: { passed: { type: 'boolean' }, issues: { type: 'array', items: { type: 'string' } } },
  required: ['passed', 'issues']
}

export async function run(statePath, agentFn) {
  const state = await readState(statePath)
  const { output_dir: out, project, memo_path, agent_context_path } = state

  const result = {
    structural: { passed: true, checks: [] },
    qc: { passed: true, issues: [], skipped: !agentFn },
    visual: { passed: true, issues: [] },
    additional: {
      bootstrap_present: false,
      agent_context_exists: false,
      citation_index_exists: false,
      catalog_integrity: true
    },
    overall: false
  }

  // Stage 1: Structural (always runs — no SDK needed)
  const REQUIRED_SECTIONS = ['bootstrap','executive-summary','deliverables','current-state',
    'technical-decisions','challenges-blockers','next-steps','context-sources',
    'open-questions','dependencies','environment','testing','architecture','data-flow','changelog']

  try {
    const html = await readFile(memo_path, 'utf8')
    for (const id of REQUIRED_SECTIONS) {
      if (!html.includes(`id="${id}"`)) {
        result.structural.passed = false
        result.structural.checks.push(`Missing section: #${id}`)
      }
    }
    if (state.risk_flags_count > 0 && !html.includes('id="privacy-security"')) {
      result.structural.passed = false
      result.structural.checks.push('Missing #privacy-security section (risk_flags_count > 0)')
    }
    result.additional.bootstrap_present = html.includes('id="bootstrap"')
  } catch (e) {
    result.structural.passed = false
    result.structural.checks.push(`Cannot read memo: ${e.message}`)
  }

  // Additional checks (always run — no SDK needed)
  result.additional.agent_context_exists = await stat(agent_context_path).then(() => true).catch(() => false)
  const citationPath = join(out, '.handoff', `${project}-citation-index.json`)
  result.additional.citation_index_exists = await stat(citationPath).then(() => true).catch(() => false)

  // Catalog copy integrity (always runs — no SDK needed)
  for (const e of (state.file_inventory || []).filter(x => x.action === 'copy' && x.sha256)) {
    try {
      const dest = join(out, e.dest_rel_path)
      const buf = await readFile(dest)
      const actual = createHash('sha256').update(buf).digest('hex')
      if (actual !== e.sha256) {
        result.additional.catalog_integrity = false
        result.structural.checks.push(`SHA256 mismatch: ${e.rel_path}`)
      }
    } catch {}
  }

  // Stage 2: QC — requires agentFn; skipped in no-SDK / checkpoint mode
  if (agentFn && result.structural.passed && memo_path) {
    const html = await readFile(memo_path, 'utf8').catch(() => '')
    const qcPrompt = `Review this handoff memo for quality. Check: coherence, completeness, that all sections have meaningful content (not just headers), and that next-steps are actionable. Return JSON.\n\nMemo (first 15000 chars):\n${html.slice(0, 15000)}`
    const qc = await agentFn(qcPrompt, { schema: CHECK_SCHEMA, label: 'verify-qc' })
    if (qc) { result.qc = { ...qc, skipped: false } }
  }

  // Stage 3: Visual link check (always runs — no SDK needed)
  if (result.qc.passed && memo_path) {
    const html = await readFile(memo_path, 'utf8').catch(() => '')
    const htmlNoScript = html.replace(/<script[\s\S]*?<\/script>/gi, '')
    const navLinks = [...htmlNoScript.matchAll(/href="#([^"]+)"/g)].map(m => m[1])
    const sectionIds = [...htmlNoScript.matchAll(/id="([^"]+)"/g)].map(m => m[1])
    const broken = navLinks.filter(id => !sectionIds.includes(id))
    if (broken.length) {
      result.visual.passed = false
      result.visual.issues = broken.map(id => `Broken nav link: #${id}`)
    }
  }

  result.overall = result.structural.passed && result.qc.passed && result.visual.passed
    && result.additional.bootstrap_present && result.additional.agent_context_exists
    && result.additional.citation_index_exists

  const verificationPath = join(out, '.handoff', 'verification.json')
  await mkdir(join(out, '.handoff'), { recursive: true })
  await writeFile(verificationPath, JSON.stringify(result, null, 2))

  state.verification_path = verificationPath
  state.verified = result.overall
  state.phases_completed.push('verify')
  await writeState(statePath, state)
  console.log(`✓ Verification: ${result.overall ? 'PASSED' : 'FAILED'}${result.qc.skipped ? ' (QC skipped — no SDK)' : ''}`)
  if (!result.overall) {
    if (!result.structural.passed) result.structural.checks.forEach(c => console.log(`  ✗ ${c}`))
    if (!result.qc.passed) result.qc.issues.forEach(i => console.log(`  QC: ${i}`))
    if (!result.visual.passed) result.visual.issues.forEach(i => console.log(`  Visual: ${i}`))
  }
}
