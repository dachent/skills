import { readFile } from 'node:fs/promises'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const TEMPLATES = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'templates')

export async function renderMemo(sectionJsonMap, state) {
  const [styles, script] = await Promise.all([
    readFile(join(TEMPLATES, 'styles.css'), 'utf8'),
    readFile(join(TEMPLATES, 'script.js'), 'utf8')
  ])
  const nav = Object.keys(sectionJsonMap)
    .map(id => `<a href="#${id}">${sectionJsonMap[id].title || id}</a>`)
    .join('\n')
  const sections = Object.entries(sectionJsonMap)
    .map(([id, sec]) => `<section id="${id}"><h2>${sec.title || id}</h2>${sec.content || ''}</section>`)
    .join('\n')
  return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>${state.project} — Handoff Memo</title>
<style>${styles}</style></head>
<body>
<nav id="sidebar">${nav}</nav>
<main>${sections}</main>
<script>${script}</script>
</body></html>`
}

export function renderCatalogHtml(entries) {
  const rows = entries.map(e =>
    `<tr><td>${e.rel_path}</td><td>${e.bucket}</td><td>${e.action}</td><td>${e.risk_flags.length ? '⚠' : ''}</td></tr>`
  ).join('\n')
  return `<table><thead><tr><th>Path</th><th>Bucket</th><th>Action</th><th>Risk</th></tr></thead><tbody>${rows}</tbody></table>`
}
