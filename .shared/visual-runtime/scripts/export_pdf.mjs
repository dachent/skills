#!/usr/bin/env node
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

function usage(exitCode = 0) {
  console.log(`
Usage:
  node scripts/export_pdf.mjs --url <url> --output <file>
  node scripts/export_pdf.mjs --html <file> --output <file>

Options:
  --viewport <WxH>        Browser viewport. Defaults to 1440x900.
  --wait-until <state>    load, domcontentloaded, networkidle, or commit. Defaults to networkidle.
  --timeout <ms>          Navigation timeout. Defaults to 30000.
`.trim());
  process.exit(exitCode);
}

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === '--help' || item === '-h') {
      usage(0);
    }
    if (!item.startsWith('--')) {
      throw new Error(`Unexpected positional argument: ${item}`);
    }
    const key = item.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith('--')) {
      args[key] = true;
    } else {
      args[key] = next;
      i += 1;
    }
  }
  return args;
}

function parseViewport(value) {
  const match = String(value ?? '1440x900').match(/^(\d+)x(\d+)$/);
  if (!match) {
    throw new Error(`Invalid viewport '${value}'. Expected WIDTHxHEIGHT.`);
  }
  return { width: Number(match[1]), height: Number(match[2]) };
}

function targetFromArgs(args) {
  if (args.url && args.html) {
    throw new Error('Use only one of --url or --html.');
  }
  if (args.url) {
    return String(args.url);
  }
  if (args.html) {
    return pathToFileURL(path.resolve(String(args.html))).href;
  }
  throw new Error('Missing --url or --html.');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.output) {
    throw new Error('Missing --output.');
  }

  const target = targetFromArgs(args);
  const outputPath = path.resolve(String(args.output));
  await mkdir(path.dirname(outputPath), { recursive: true });

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: parseViewport(args.viewport) });
    await page.goto(target, {
      waitUntil: String(args['wait-until'] ?? 'networkidle'),
      timeout: Number(args.timeout ?? 30000)
    });
    await page.pdf({
      path: outputPath,
      printBackground: true,
      preferCSSPageSize: true
    });
    console.log(JSON.stringify({
      tool: 'export_pdf',
      target,
      output_path: outputPath,
      generated_at: new Date().toISOString()
    }, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
