#!/usr/bin/env node
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

function usage(exitCode = 0) {
  console.log(`
Usage:
  node scripts/visual_lint.mjs --url <url> --output visual-lint.json
  node scripts/visual_lint.mjs --html <file> --output visual-lint.json

Options:
  --viewport <WxH>        Browser viewport. Defaults to 1440x900.
  --wait-until <state>    load, domcontentloaded, networkidle, or commit. Defaults to networkidle.
  --timeout <ms>          Navigation timeout. Defaults to 30000.
  --warn-only             Always exit 0 even when findings exist.
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

  const consoleFindings = [];
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: parseViewport(args.viewport) });
    page.on('console', (message) => {
      if (['error', 'warning'].includes(message.type())) {
        consoleFindings.push({
          rule: 'console_event',
          severity: message.type() === 'error' ? 'major' : 'minor',
          message: message.text(),
          location: message.location()
        });
      }
    });
    page.on('pageerror', (error) => {
      consoleFindings.push({
        rule: 'page_error',
        severity: 'major',
        message: error.message,
        location: {}
      });
    });

    await page.goto(target, {
      waitUntil: String(args['wait-until'] ?? 'networkidle'),
      timeout: Number(args.timeout ?? 30000)
    });

    const domFindings = await page.evaluate(() => {
      function selectorFor(element) {
        if (element.id) {
          return `#${element.id}`;
        }
        const parts = [];
        let current = element;
        while (current && current.nodeType === Node.ELEMENT_NODE && parts.length < 4) {
          let part = current.tagName.toLowerCase();
          if (current.classList.length > 0) {
            part += `.${Array.from(current.classList).slice(0, 2).join('.')}`;
          }
          parts.unshift(part);
          current = current.parentElement;
        }
        return parts.join(' > ');
      }

      function parseRgb(value) {
        const match = String(value).match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
        if (!match) {
          return null;
        }
        return [Number(match[1]), Number(match[2]), Number(match[3])];
      }

      function luminance(rgb) {
        const parts = rgb.map((part) => {
          const channel = part / 255;
          return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2];
      }

      function contrastRatio(foreground, background) {
        const first = luminance(foreground);
        const second = luminance(background);
        const lighter = Math.max(first, second);
        const darker = Math.min(first, second);
        return (lighter + 0.05) / (darker + 0.05);
      }

      function resolvedBackground(element) {
        let current = element;
        while (current) {
          const color = getComputedStyle(current).backgroundColor;
          if (color && color !== 'transparent' && !color.endsWith(', 0)')) {
            return color;
          }
          current = current.parentElement;
        }
        return 'rgb(255, 255, 255)';
      }

      function isVisible(element) {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          Number(style.opacity) > 0 &&
          rect.width > 0 &&
          rect.height > 0;
      }

      const findings = [];
      for (const element of Array.from(document.querySelectorAll('body *'))) {
        if (!isVisible(element)) {
          continue;
        }

        const text = (element.innerText || '').trim().replace(/\s+/g, ' ');
        const selector = selectorFor(element);
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        if (text && (element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1)) {
          findings.push({
            rule: 'text_overflow',
            severity: 'major',
            selector,
            message: 'Element text appears clipped or scrollable.',
            sample: text.slice(0, 120),
            bounds: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
          });
        }

        const fontSize = Number.parseFloat(style.fontSize);
        if (text && fontSize > 0 && fontSize < 11) {
          findings.push({
            rule: 'tiny_text',
            severity: 'minor',
            selector,
            message: `Text is ${fontSize}px, which is likely too small for general UI reading.`,
            sample: text.slice(0, 120)
          });
        }

        const foreground = parseRgb(style.color);
        const background = parseRgb(resolvedBackground(element));
        if (text && foreground && background) {
          const ratio = contrastRatio(foreground, background);
          const threshold = fontSize >= 18 ? 3 : 4.5;
          if (ratio < threshold) {
            findings.push({
              rule: 'low_contrast',
              severity: 'major',
              selector,
              message: `Contrast ratio ${ratio.toFixed(2)} is below ${threshold}.`,
              sample: text.slice(0, 120)
            });
          }
        }

        if (element.tagName.toLowerCase() === 'img') {
          const image = element;
          if (!image.getAttribute('alt')) {
            findings.push({
              rule: 'missing_image_alt',
              severity: 'minor',
              selector,
              message: 'Image is missing alt text.'
            });
          }
          if (image.naturalWidth === 0 || image.naturalHeight === 0) {
            findings.push({
              rule: 'broken_image',
              severity: 'major',
              selector,
              message: 'Image did not load.'
            });
          }
        }
      }
      return findings;
    });

    const result = {
      tool: 'visual_lint',
      target,
      viewport: parseViewport(args.viewport),
      finding_count: consoleFindings.length + domFindings.length,
      findings: [...consoleFindings, ...domFindings],
      generated_at: new Date().toISOString()
    };

    await writeFile(outputPath, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
    console.log(JSON.stringify(result, null, 2));

    if (result.finding_count > 0 && args['warn-only'] !== true) {
      process.exit(2);
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
