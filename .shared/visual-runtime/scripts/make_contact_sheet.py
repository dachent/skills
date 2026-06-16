from __future__ import annotations

import argparse
import html
import os
from pathlib import Path

from image_bounds import collect_images, inspect_image


def image_source(path: Path, output_path: Path, absolute: bool) -> str:
    if absolute:
        return path.resolve().as_uri()
    return os.path.relpath(path.resolve(), output_path.parent.resolve()).replace(os.sep, "/")


def build_html(title: str, rows: list[dict], output_path: Path, absolute: bool) -> str:
    cards: list[str] = []
    for row in rows:
        path = Path(row["path"])
        safe_path = html.escape(str(path))
        if row.get("ok"):
            src = html.escape(image_source(path, output_path, absolute))
            meta = f'{row["width"]} x {row["height"]} px, {row["bytes"]} bytes'
            cards.append(
                f"""
        <article class="card">
          <img src="{src}" alt="{safe_path}">
          <h2>{html.escape(path.name)}</h2>
          <p>{html.escape(meta)}</p>
          <code>{safe_path}</code>
        </article>"""
            )
        else:
            cards.append(
                f"""
        <article class="card error">
          <div class="placeholder">Image unavailable</div>
          <h2>{html.escape(path.name)}</h2>
          <p>{html.escape(str(row.get("error", "unknown error")))}</p>
          <code>{safe_path}</code>
        </article>"""
            )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)}</title>
    <style>
      body {{
        margin: 0;
        font-family: Arial, sans-serif;
        background: #f6f7fb;
        color: #172033;
      }}
      main {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 32px 20px;
      }}
      h1 {{
        margin: 0 0 20px;
        font-size: 28px;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
        gap: 16px;
      }}
      .card {{
        background: #ffffff;
        border: 1px solid #d9dee8;
        border-radius: 8px;
        padding: 12px;
      }}
      .card img,
      .placeholder {{
        width: 100%;
        aspect-ratio: 16 / 10;
        object-fit: contain;
        background: #eef1f6;
        border: 1px solid #e3e7ef;
        border-radius: 6px;
      }}
      .placeholder {{
        display: grid;
        place-items: center;
        color: #6b7280;
      }}
      h2 {{
        margin: 10px 0 4px;
        font-size: 16px;
      }}
      p {{
        margin: 0 0 8px;
        color: #4b5563;
      }}
      code {{
        display: block;
        overflow-wrap: anywhere;
        color: #374151;
        font-size: 12px;
      }}
      .error {{
        border-color: #ef4444;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>{html.escape(title)}</h1>
      <section class="grid">
{''.join(cards)}
      </section>
    </main>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an HTML contact sheet for visual QA evidence.")
    parser.add_argument("paths", nargs="+", help="Image files or directories to include.")
    parser.add_argument("--output", required=True, help="HTML output path.")
    parser.add_argument("--title", default="Visual QA Contact Sheet", help="Contact sheet title.")
    parser.add_argument("--absolute", action="store_true", help="Use absolute file URIs for image sources.")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = collect_images(Path(item) for item in args.paths)
    rows = [inspect_image(path) for path in images]
    output_path.write_text(build_html(args.title, rows, output_path, args.absolute), encoding="utf-8")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
