export const meta = {
  name: 'handoff-verification',
  description: 'Three-stage verification: structural checks, multi-axis QC, Chrome visual review',
  phases: [
    { title: 'Structural', detail: 'Automated HTML integrity checks' },
    { title: 'QC',         detail: 'Multi-axis content quality review' },
    { title: 'Visual',     detail: 'Chrome render + visual review agent' },
  ],
}

const _args = typeof args === 'string' ? JSON.parse(args) : args
const { project, output_dir, state } = _args
const { approved_sections, memo_path, synthesis_path, digests_path } = state

const CHECK_SCHEMA = {
  type: 'object',
  required: ['passed', 'failures', 'warnings'],
  properties: {
    passed:   { type: 'boolean' },
    failures: {
      type: 'array',
      items: {
        type: 'object',
        required: ['check', 'detail'],
        properties: { check: { type: 'string' }, detail: { type: 'string' } }
      }
    },
    warnings: { type: 'array', items: { type: 'string' } },
  }
}

phase('Structural')

const structural = await agent(
  `Run structural validation on the HTML memo file.

File: ${memo_path}
Approved sections: ${JSON.stringify(approved_sections)}

Read the file. Run every check below. Return structured results.

CHECKS (add a failures entry for each that fails):
1. "sections_present" — every anchor in approved_sections has a matching <section id="..."> element
2. "internal_links" — every href="#..." in the sidebar nav has a matching id="..." in the document
3. "no_empty_sections" — every <section> element contains at least 200 characters of visible text (strip HTML tags before counting)
4. "css_present" — a non-empty <style> block exists in <head>
5. "file_size_ok" — file is larger than 10000 bytes
6. "no_placeholders" — no occurrences of: TODO, TBD, [PLACEHOLDER], [INSERT], [FILL IN], [ADD CONTENT]
7. "sidebar_toc_match" — nav sidebar links match approved_sections (same anchors, order may differ)
8. "no_entity_leaks" — no occurrences of literal "&amp;" or "&lt;" outside <code> or <pre> blocks

Set passed: true only when failures is empty.`,
  { label: 'stage1-structural', schema: CHECK_SCHEMA }
)

if (!structural.passed) {
  return { stage: 1, passed: false, structural }
}

phase('QC')

const QC_RESULT_SCHEMA = {
  type: 'object',
  required: ['passed', 'section_results', 'overall_summary'],
  properties: {
    passed:          { type: 'boolean' },
    overall_summary: { type: 'string' },
    section_results: {
      type: 'array',
      items: {
        type: 'object',
        required: ['section', 'content_quality', 'consistency', 'source_fidelity', 'self_contained', 'verdict', 'issues'],
        properties: {
          section:         { type: 'string' },
          content_quality: { enum: ['pass', 'warning', 'fail'] },
          consistency:     { enum: ['pass', 'warning', 'fail'] },
          source_fidelity: { enum: ['pass', 'warning', 'fail'] },
          self_contained:  { enum: ['pass', 'warning', 'fail'] },
          verdict:         { enum: ['pass', 'warning', 'fail'] },
          issues:          { type: 'array', items: { type: 'string' } },
        }
      }
    }
  }
}

const qc = await agent(
  `Perform multi-axis quality review of the handoff memo.

Memo: ${memo_path}
Synthesis: ${synthesis_path}
Digests: ${digests_path}
Approved sections: ${JSON.stringify(approved_sections)}

Read all files. For each section, evaluate on 4 axes. Set verdict = worst of the 4.

AXIS 1 — CONTENT QUALITY
- Does the section have substantive, specific content (not generic boilerplate)?
- If #runbook: are commands complete and executable?
- If #modules: do entries have real signatures/names?
- If #challenges: does each challenge have a resolution or current status?

AXIS 2 — CROSS-SECTION CONSISTENCY
- Are decisions in #decisions traceable to challenges in #challenges?
- Does #scope describe the same project as #state?
- Does #flow show paths that have corresponding runbook entries?

AXIS 3 — SOURCE FIDELITY
- Are key files from synthesis.md referenced in the memo?
- Are key decisions from digests surfaced in relevant sections?
- Is any high-importance finding from synthesis missing entirely?

AXIS 4 — SELF-CONTAINMENT
- Could a person with no other context reconstruct this project using only this memo?
- What specific information would they be missing?

Rate each axis: pass / warning / fail. verdict = worst of 4.
Set passed: true only when no section has verdict = fail.`,
  { label: 'stage2-qc', schema: QC_RESULT_SCHEMA }
)

if (!qc.passed) {
  return { stage: 2, passed: false, structural, qc }
}

phase('Visual')

const VISUAL_SCHEMA = {
  type: 'object',
  required: ['passed', 'blockers', 'warnings', 'cosmetic'],
  properties: {
    passed:   { type: 'boolean' },
    blockers: { type: 'array', items: { type: 'string' } },
    warnings: { type: 'array', items: { type: 'string' } },
    cosmetic: { type: 'array', items: { type: 'string' } },
  }
}

const memoUrl = 'file:///' + memo_path.replace(/\\/g, '/')

const visual = await agent(
  `Perform visual review of the handoff memo.

Steps:
1. Navigate to: ${memoUrl}  — use mcp__Claude_in_Chrome__navigate
2. Take a screenshot of the initial page load
3. For each section anchor in [${approved_sections.join(', ')}]:
   - Use mcp__Claude_in_Chrome__javascript_tool with: document.querySelector('section#ANCHOR').scrollIntoView()
   - Replace ANCHOR with the anchor name (without #)
   - Take a screenshot after scrolling
4. Evaluate screenshots for:

BLOCKERS (memo unusable):
- Main layout broken (sidebar and content not side by side)
- Any section invisible or not rendered
- Sidebar nav missing or showing no links
- Page blank or showing an error

WARNINGS (usability impaired):
- Text overflow outside containers
- A section appears nearly empty
- Sidebar links do not highlight on scroll
- Significant contrast issues

COSMETIC (minor):
- Minor spacing inconsistencies
- Small alignment issues

Set passed: true if blockers is empty.`,
  { label: 'stage3-visual', schema: VISUAL_SCHEMA }
)

return {
  stage:  'complete',
  passed: structural.passed && qc.passed && visual.passed,
  structural,
  qc,
  visual,
}
