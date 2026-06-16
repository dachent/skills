from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Iterable


IMAGE_EXTENSIONS = {".gif", ".jpeg", ".jpg", ".png"}


def read_png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a PNG file")
        length = struct.unpack(">I", handle.read(4))[0]
        chunk_type = handle.read(4)
        if chunk_type != b"IHDR" or length < 8:
            raise ValueError("missing PNG IHDR chunk")
        width, height = struct.unpack(">II", handle.read(8))
        return width, height


def read_gif_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(10)
        if not (header.startswith(b"GIF87a") or header.startswith(b"GIF89a")):
            raise ValueError("not a GIF file")
        width, height = struct.unpack("<HH", header[6:10])
        return width, height


def read_jpeg_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(2) != b"\xff\xd8":
            raise ValueError("not a JPEG file")

        while True:
            marker_start = handle.read(1)
            if marker_start == b"":
                raise ValueError("JPEG size marker not found")
            if marker_start != b"\xff":
                continue

            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)

            if marker in {b"\xd8", b"\xd9"}:
                continue

            segment_length_bytes = handle.read(2)
            if len(segment_length_bytes) != 2:
                raise ValueError("truncated JPEG segment")
            segment_length = struct.unpack(">H", segment_length_bytes)[0]
            if segment_length < 2:
                raise ValueError("invalid JPEG segment length")

            if marker in {
                b"\xc0",
                b"\xc1",
                b"\xc2",
                b"\xc3",
                b"\xc5",
                b"\xc6",
                b"\xc7",
                b"\xc9",
                b"\xca",
                b"\xcb",
                b"\xcd",
                b"\xce",
                b"\xcf",
            }:
                data = handle.read(5)
                if len(data) != 5:
                    raise ValueError("truncated JPEG frame header")
                height, width = struct.unpack(">HH", data[1:5])
                return width, height

            handle.seek(segment_length - 2, 1)


def collect_images(paths: Iterable[Path]) -> list[Path]:
    images: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved.is_dir():
            images.extend(
                item
                for item in sorted(resolved.rglob("*"))
                if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
            )
        elif resolved.is_file() and resolved.suffix.lower() in IMAGE_EXTENSIONS:
            images.append(resolved)
        else:
            images.append(resolved)
    return images


def inspect_image(path: Path) -> dict:
    suffix = path.suffix.lower()
    if not path.is_file():
        return {
            "path": str(path),
            "ok": False,
            "error": "file_not_found",
        }

    try:
        if suffix == ".png":
            width, height = read_png_size(path)
            image_type = "png"
        elif suffix == ".gif":
            width, height = read_gif_size(path)
            image_type = "gif"
        elif suffix in {".jpg", ".jpeg"}:
            width, height = read_jpeg_size(path)
            image_type = "jpeg"
        else:
            raise ValueError(f"unsupported extension: {suffix}")
    except Exception as exc:
        return {
            "path": str(path),
            "ok": False,
            "error": str(exc),
        }

    stat = path.stat()
    return {
        "path": str(path),
        "ok": True,
        "type": image_type,
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 6) if height else None,
        "bytes": stat.st_size,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect image dimensions for visual QA evidence.")
    parser.add_argument("paths", nargs="+", help="Image files or directories to inspect.")
    parser.add_argument("--json", dest="json_path", help="Optional JSON output path.")
    parser.add_argument("--fail-on-error", action="store_true", help="Exit 2 when any image cannot be inspected.")
    args = parser.parse_args(argv)

    images = collect_images(Path(item) for item in args.paths)
    results = [inspect_image(path) for path in images]
    payload = {
        "tool": "image_bounds",
        "count": len(results),
        "error_count": sum(1 for item in results if not item.get("ok")),
        "images": results,
    }
    output = json.dumps(payload, indent=2)

    if args.json_path:
        Path(args.json_path).write_text(f"{output}\n", encoding="utf-8")
    print(output)

    if args.fail_on_error and payload["error_count"] > 0:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
