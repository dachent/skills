# HTML Rendering

## Template files

- `templates/styles.css` — all CSS; inlined into memo `<style>` tag
- `templates/script.js` — IntersectionObserver sidebar highlight; inlined into memo `<script>` tag

## renderMemo contract

Input: sectionJsonMap (Record<id, SectionJSON>), state (StateObject)
Output: complete HTML string with inlined CSS + JS (built directly, no shell template)

## Section rendering

For each section JSON object:

```html
<section id="{id}">
  <h2>{title}</h2>
  {content}   ← raw HTML fragment from agent JSON
</section>
```

## Nav rendering

```html
<nav id="sidebar">
  <a href="#bootstrap">Quick-Start Bootstrap</a>
  <a href="#executive-summary">Executive Summary</a>
  ...
</nav>
```

## agent-context.json schema

Written alongside memo.html. Enables agent cold-start without re-reading the memo.

```json
{
  "project": "string",
  "generated_at": "ISO-8601",
  "section_references": {
    "bootstrap": { "catalog_ids": [], "summary": "string" },
    "next-steps": { "catalog_ids": [], "summary": "string" }
  },
  "citation_index_path": "string — path to {project}-citation-index.json"
}
```
