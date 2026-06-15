export const meta = {
  name: 'handoff-section-writers',
  description: 'Write parallel HTML section fragments for the handoff memo',
  phases: [{ title: 'Write Sections', detail: 'One agent per approved section' }],
}

const _args = typeof args === 'string' ? JSON.parse(args) : args
const { project, output_dir, state } = _args
const { approved_sections, digests_path, synthesis_path, catalog_path } = state
const tmp = `${output_dir}\\.handoff\\tmp`

const SECTION_CONTENT = {
  '#overview':   `stats dashboard: project name "${project}", total file/session counts from the catalog, a status badge (Verified or In Progress), and a <div class="stats-grid"> with <div class="stat-card"> tiles for key metrics. Read ${catalog_path} for file counts.`,
  '#flow':       `data and system flow: describe how data moves inputs→processing→outputs using an ASCII diagram inside <pre><code>. Read ${synthesis_path} for flow details.`,
  '#scope':      `scope and context: why this project was done, what problem it solves, constraints, who uses the outputs. Read ${synthesis_path}.`,
  '#state':      `system state: current state of deliverables, what "done" means, key metrics proving completion, known limitations. Read ${synthesis_path}.`,
  '#runbook':    `task runbook: every operation needed to run/update/validate the project. For each workflow: name, trigger, exact commands, expected output. Use <ol> for numbered steps. Read ${synthesis_path} and ${digests_path}.`,
  '#modules':    `module or component API: list all source modules with purpose, key functions/classes, tier (depth-1 core / depth-2 utility / depth-3 internal). Group by tier. Read ${synthesis_path} and ${digests_path}.`,
  '#tests':      `tests and validation: test suite structure, coverage stats if available, validation procedures, known gaps. Read ${synthesis_path} and ${digests_path}.`,
  '#decisions':  `planning decisions: what was decided before implementation (grill-me and brainstorm outputs), constraints that shaped the approach, architectural choices. Read ${synthesis_path}.`,
  '#missed':     `what the plan missed: gaps found during execution vs the original plan, improvements identified, what would be done differently. Be specific. Read ${synthesis_path} and ${digests_path}.`,
  '#challenges': `challenges: every significant challenge tagged <span class="badge badge-seeded">SEEDED</span> or <span class="badge badge-discovered">DISCOVERED</span>. For each: description, impact, resolution. Read ${synthesis_path} and ${digests_path}.`,
  '#config':     `configuration: config files, environment variables, override mechanisms, file maps, external dependencies. Include file paths and key values. Read ${synthesis_path} and ${digests_path}.`,
  '#improvements':  `recommendations for improvement and optimization: analyze what worked well and what didn't in this project. What tools, approaches, or processes should be changed next time? What technical debt was introduced? What would make this faster, more reliable, or easier to maintain? Be specific and actionable. Read ${synthesis_path} and ${digests_path}.`,
  '#productionize': `production process recommendation: how to convert this one-time project into a recurring automated process. What should be scheduled? What monitoring and alerting is needed? What manual steps remain and should they be automated? What are the dependencies, prerequisites, and failure modes? Provide a concrete actionable roadmap. Read ${synthesis_path} and ${digests_path}.`,
  '#catalog':    `file catalog reference: link to the catalog file, workfolder directory tree in <pre><code>, key file paths by category. Read ${catalog_path}.`,
}

const CSS_TEMPLATE_PATH = 'C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\templates\\css-dark.html'

phase('Write Sections')

const navLinks = approved_sections
  .map(a => `  <a href="${a}">${a.replace('#', '')}</a>`)
  .join('\n')

const tasks = approved_sections.map((anchor, i) => {
  const isFirst = i === 0
  const isLast  = i === approved_sections.length - 1
  const num     = String(i + 1).padStart(2, '0')
  const name    = anchor.replace('#', '')
  const outFile = `${tmp}\\sec_${num}_${name}.html`
  const content = SECTION_CONTENT[anchor] || `write a section for "${anchor}" using content from ${synthesis_path} and ${digests_path}`
  const title   = name.charAt(0).toUpperCase() + name.slice(1)

  if (isFirst) {
    return () => agent(
      `Write the OPENING HTML fragment for the ${project} handoff memo.

Output file: ${outFile}

Step 1: Read the CSS template file at: ${CSS_TEMPLATE_PATH}
It contains raw CSS text followed by </style><script>...</script>

Step 2: Write this complete content to the output file:

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${project} — Handoff Memo</title>
<style>
[EMBED the full contents of ${CSS_TEMPLATE_PATH} verbatim here — the file starts with CSS rules and ends with </style><script>...</script>]
</head>
<body>
<nav id="sidebar">
  <h2>${project}</h2>
${navLinks}
</nav>
<main>
<section id="${name}">
<h1>${title}</h1>
[Write section body: ${content}]
</section>`,
      { label: `write:${anchor}` }
    )
  }

  if (isLast) {
    return () => agent(
      `Write the CLOSING HTML fragment for the ${project} handoff memo.

Output file: ${outFile}

Write this content to the file:

<section id="${name}">
<h1>${title}</h1>
[Write section body: ${content}]
</section>
</main>
<footer>Generated by document-handoff skill</footer>
</body>
</html>`,
      { label: `write:${anchor}` }
    )
  }

  return () => agent(
    `Write an HTML section fragment for the ${project} handoff memo.

Output file: ${outFile}

Write ONLY this block — no DOCTYPE, html, head, or body tags:

<section id="${name}">
<h1>${title}</h1>
[Write section body: ${content}]
</section>`,
    { label: `write:${anchor}` }
  )
})

await parallel(tasks)

return { sections_written: approved_sections.length, tmp_dir: tmp }
