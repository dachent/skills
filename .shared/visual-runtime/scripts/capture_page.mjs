#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

function usage(exitCode = 0) {
  const text = `
Usage:
  node scripts/capture_page.mjs --url <url> --out-dir <dir> [--viewport 1440x900] [--pdf]
  node scripts/capture_page.mjs --html <file> --out-dir <dir> [--viewport 390x844]

Options:
  --url <url>             URL to render.
  --html <file>           Local HTML file to render.
  --out-dir <dir>         Output directory. Defaults to visual-capture.
  --viewport <WxH>        Browser viewport. Defaults to 1440x900.
  --wait-until <state>    load, domcontentloaded, networkidle, or commit. Defaults to networkidle.
  --timeout <ms>          Navigation timeout. Defaults to 30000.
  --wait-ms <ms>          Extra wait after navigation. Defaults to 0.
  --device-scale <n>      Device scale factor. Defaults to 1.
  --viewport-only         Capture only the viewport instead of full page.
  --pdf                   Also export page.pdf.
`;
  console.log(text.trim());
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
  return {
    width: Number(match[1]),
    height: Number(match[2])
  };
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
  const target = targetFromArgs(args);
  const viewport = parseViewport(args.viewport);
  const outDir = path.resolve(String(args['out-dir'] ?? 'visual-capture'));
  const waitUntil = String(args['wait-until'] ?? 'networkidle');
  const timeout = Number(args.timeout ?? 30000);
  const waitMs = Number(args['wait-ms'] ?? 0);
  const deviceScaleFactor = Number(args['device-scale'] ?? 1);

  await mkdir(outDir, { recursive: true });

  const screenshotPath = path.join(outDir, 'screenshot.png');
  const pdfPath = path.join(outDir, 'page.pdf');
  const consolePath = path.join(outDir, 'console-events.json');
  const failuresPath = path.join(outDir, 'request-failures.json');
  const manifestPath = path.join(outDir, 'manifest.json');
  const consoleEvents = [];
  const requestFailures = [];

  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport, deviceScaleFactor });
    page.on('console', (message) => {
      consoleEvents.push({
        type: message.type(),
        text: message.text(),
        location: message.location()
      });
    });
    page.on('pageerror', (error) => {
      consoleEvents.push({
        type: 'pageerror',
        text: error.message,
        location: {}
      });
    });
    page.on('requestfailed', (request) => {
      requestFailures.push({
        url: request.url(),
        method: request.method(),
        failure: request.failure()?.errorText ?? 'unknown'
      });
    });

    await page.goto(target, { waitUntil, timeout });
    if (waitMs > 0) {
      await page.waitForTimeout(waitMs);
    }

    const title = await page.title();
    await page.screenshot({
      path: screenshotPath,
      fullPage: args['viewport-only'] !== true
    });

    if (args.pdf === true) {
      await page.pdf({
        path: pdfPath,
        printBackground: true,
        preferCSSPageSize: true
      });
    }

    const manifest = {
      tool: 'capture_page',
      target,
      title,
      viewport,
      device_scale_factor: deviceScaleFactor,
      screenshot_path: screenshotPath,
      pdf_path: args.pdf === true ? pdfPath : null,
      console_events_path: consolePath,
      request_failures_path: failuresPath,
      console_event_count: consoleEvents.length,
      request_failure_count: requestFailures.length,
      generated_at: new Date().toISOString()
    };

    await writeFile(consolePath, `${JSON.stringify(consoleEvents, null, 2)}\n`, 'utf8');
    await writeFile(failuresPath, `${JSON.stringify(requestFailures, null, 2)}\n`, 'utf8');
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(manifest, null, 2));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
