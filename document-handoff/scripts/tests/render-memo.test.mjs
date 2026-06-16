import { test } from 'node:test'
import assert from 'node:assert/strict'
import { renderMemo } from '../lib/html.mjs'

const MOCK_STATE = { project: 'render-test', risk_flags_count: 0 }
const SECTIONS = {
  'bootstrap': { id: 'bootstrap', title: 'Bootstrap', content: '<p>entry: node cli.mjs</p>', catalog_ids_referenced: ['src/main.ts'] },
  'executive-summary': { id: 'executive-summary', title: 'Summary', content: '<p>Project done.</p>', catalog_ids_referenced: [] }
}

test('renderMemo: each section id appears as HTML id', async () => {
  const html = await renderMemo(SECTIONS, MOCK_STATE)
  assert.ok(html.includes('id="bootstrap"'))
  assert.ok(html.includes('id="executive-summary"'))
})

test('renderMemo: #bootstrap section is present', async () => {
  const html = await renderMemo(SECTIONS, MOCK_STATE)
  assert.ok(html.includes('id="bootstrap"'))
  assert.ok(html.includes('entry: node cli.mjs'))
})

test('renderMemo: nav links generated for each section', async () => {
  const html = await renderMemo(SECTIONS, MOCK_STATE)
  assert.ok(html.includes('href="#bootstrap"'))
  assert.ok(html.includes('href="#executive-summary"'))
})

test('renderMemo: privacy-security section included when risk_flags_count > 0', async () => {
  const withRisk = { ...MOCK_STATE, risk_flags_count: 2 }
  const sections = {
    ...SECTIONS,
    'privacy-security': { id: 'privacy-security', title: 'Privacy & Security', content: '<table><tr><td>.env</td></tr></table>', catalog_ids_referenced: ['.env'] }
  }
  const html = await renderMemo(sections, withRisk)
  assert.ok(html.includes('id="privacy-security"'))
})
