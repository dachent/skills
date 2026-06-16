from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
EMU_PER_INCH = 914400
SLIDE_RE = re.compile(r"ppt/slides/slide(\d+)\.xml$")


def read_xml(archive: zipfile.ZipFile, name: str) -> ET.Element | None:
    try:
        with archive.open(name) as handle:
            return ET.fromstring(handle.read())
    except KeyError:
        return None
    except ET.ParseError as exc:
        raise RuntimeError(f"Invalid XML in {name}: {exc}") from exc


def normalize_part(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        target = target.lstrip("/")
    else:
        target = posixpath.normpath(posixpath.join(base_dir, target))
    return target.replace("\\", "/")


def relationship_map(archive: zipfile.ZipFile, rels_name: str, base_dir: str) -> dict[str, dict[str, str]]:
    root = read_xml(archive, rels_name)
    if root is None:
        return {}
    relationships: dict[str, dict[str, str]] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id", "")
        target = rel.attrib.get("Target", "")
        if not rel_id or not target:
            continue
        relationships[rel_id] = {
            "type": rel.attrib.get("Type", ""),
            "target": normalize_part(base_dir, target),
        }
    return relationships


def slide_sort_key(name: str) -> tuple[int, str]:
    match = SLIDE_RE.match(name)
    if match:
        return int(match.group(1)), name
    return sys.maxsize, name


def ordered_slides(archive: zipfile.ZipFile) -> list[str]:
    presentation = read_xml(archive, "ppt/presentation.xml")
    rels = relationship_map(archive, "ppt/_rels/presentation.xml.rels", "ppt")
    slides: list[str] = []
    if presentation is not None:
        for slide_id in presentation.findall(".//p:sldId", NS):
            rel_id = slide_id.attrib.get(f"{{{NS['r']}}}id", "")
            target = rels.get(rel_id, {}).get("target")
            if target and target in archive.namelist():
                slides.append(target)
    if slides:
        return slides
    return sorted((name for name in archive.namelist() if SLIDE_RE.match(name)), key=slide_sort_key)


def slide_size(archive: zipfile.ZipFile) -> dict[str, float | int | None]:
    presentation = read_xml(archive, "ppt/presentation.xml")
    size = presentation.find("p:sldSz", NS) if presentation is not None else None
    if size is None:
        return {
            "width_emu": None,
            "height_emu": None,
            "width_inches": None,
            "height_inches": None,
            "aspect_ratio": None,
        }
    width = int(size.attrib.get("cx", "0"))
    height = int(size.attrib.get("cy", "0"))
    width_inches = round(width / EMU_PER_INCH, 3) if width else None
    height_inches = round(height / EMU_PER_INCH, 3) if height else None
    aspect_ratio = round(width / height, 3) if width and height else None
    return {
        "width_emu": width,
        "height_emu": height,
        "width_inches": width_inches,
        "height_inches": height_inches,
        "aspect_ratio": aspect_ratio,
    }


def text_from(root: ET.Element) -> list[str]:
    return [
        text.strip()
        for text in (node.text for node in root.findall(".//a:t", NS))
        if text and text.strip()
    ]


def rel_counts(archive: zipfile.ZipFile, slide_part: str) -> dict[str, int | bool]:
    slide_dir = posixpath.dirname(slide_part)
    rels_name = f"{slide_dir}/_rels/{posixpath.basename(slide_part)}.rels"
    rels = relationship_map(archive, rels_name, slide_dir)
    counts = {
        "charts": 0,
        "images": 0,
        "notes": 0,
        "embedded_objects": 0,
    }
    for rel in rels.values():
        rel_type = rel["type"]
        if rel_type.endswith("/chart"):
            counts["charts"] += 1
        elif rel_type.endswith("/image"):
            counts["images"] += 1
        elif rel_type.endswith("/notesSlide"):
            counts["notes"] += 1
        elif rel_type.endswith("/oleObject") or rel_type.endswith("/package"):
            counts["embedded_objects"] += 1
    return {
        **counts,
        "has_notes": counts["notes"] > 0,
    }


def inspect_slide(archive: zipfile.ZipFile, slide_part: str, index: int) -> dict:
    root = read_xml(archive, slide_part)
    if root is None:
        return {"index": index, "part": slide_part, "error": "missing slide part"}
    text_blocks = text_from(root)
    relationships = rel_counts(archive, slide_part)
    return {
        "index": index,
        "part": slide_part,
        "text_block_count": len(text_blocks),
        "text_character_count": sum(len(item) for item in text_blocks),
        "tables": len(root.findall(".//a:tbl", NS)),
        "shape_count": len(root.findall(".//p:sp", NS)),
        "graphic_frame_count": len(root.findall(".//p:graphicFrame", NS)),
        **relationships,
    }


def theme_names(archive: zipfile.ZipFile) -> list[str]:
    names: list[str] = []
    for name in sorted(part for part in archive.namelist() if part.startswith("ppt/theme/theme") and part.endswith(".xml")):
        root = read_xml(archive, name)
        if root is None:
            continue
        theme_name = root.attrib.get("name")
        if theme_name:
            names.append(theme_name)
    return names


def inspect_pptx(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        slides = ordered_slides(archive)
        slide_reports = [inspect_slide(archive, slide_part, index + 1) for index, slide_part in enumerate(slides)]
        media = sorted(name for name in names if name.startswith("ppt/media/"))
        charts = sorted(name for name in names if name.startswith("ppt/charts/") and name.endswith(".xml"))
        return {
            "source_path": str(path),
            "slide_count": len(slides),
            "slide_size": slide_size(archive),
            "theme_names": theme_names(archive),
            "media_count": len(media),
            "chart_count": len(charts),
            "has_vba": "ppt/vbaProject.bin" in names,
            "has_custom_xml": any(name.startswith("customXml/") for name in names),
            "slides": slide_reports,
        }


def to_markdown(report: dict) -> str:
    size = report["slide_size"]
    lines = [
        "# PowerPoint Metadata",
        "",
        f"- Source: `{report['source_path']}`",
        f"- Slide count: {report['slide_count']}",
        f"- Slide size: {size['width_inches']} x {size['height_inches']} inches",
        f"- Aspect ratio: {size['aspect_ratio']}",
        f"- Themes: {', '.join(report['theme_names']) if report['theme_names'] else 'none detected'}",
        f"- Media files: {report['media_count']}",
        f"- Chart parts: {report['chart_count']}",
        f"- VBA project: {report['has_vba']}",
        f"- Custom XML: {report['has_custom_xml']}",
        "",
        "## Slides",
        "",
        "| Slide | Text blocks | Text chars | Shapes | Tables | Charts | Images | Notes |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for slide in report["slides"]:
        lines.append(
            "| {index} | {text_block_count} | {text_character_count} | {shape_count} | {tables} | {charts} | {images} | {has_notes} |".format(
                **slide
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_output(content: str, output_path: str | None) -> None:
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    else:
        print(content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a .pptx package without launching PowerPoint.")
    parser.add_argument("input", help="Path to the .pptx file")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Optional output path")
    args = parser.parse_args(argv)

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        report = inspect_pptx(input_path)
    except zipfile.BadZipFile:
        print(f"Input is not a valid .pptx zip package: {input_path}", file=sys.stderr)
        return 2

    content = json.dumps(report, indent=2) + "\n" if args.format == "json" else to_markdown(report)
    write_output(content, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
