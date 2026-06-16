from __future__ import annotations

import argparse
import json
import math
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
EMU_PER_POINT = 12700
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
        return target.lstrip("/")
    return posixpath.normpath(posixpath.join(base_dir, target)).replace("\\", "/")


def relationship_map(archive: zipfile.ZipFile, rels_name: str, base_dir: str) -> dict[str, dict[str, str]]:
    root = read_xml(archive, rels_name)
    if root is None:
        return {}
    result: dict[str, dict[str, str]] = {}
    for rel in root.findall("rel:Relationship", NS):
        rel_id = rel.attrib.get("Id", "")
        target = rel.attrib.get("Target", "")
        if not rel_id or not target:
            continue
        result[rel_id] = {
            "type": rel.attrib.get("Type", ""),
            "target": normalize_part(base_dir, target),
        }
    return result


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


def emu_to_points(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return int(value) / EMU_PER_POINT
    except ValueError:
        return None


def shape_name(shape: ET.Element, fallback: str) -> str:
    c_nv_pr = shape.find(".//p:cNvPr", NS)
    if c_nv_pr is not None:
        return c_nv_pr.attrib.get("name", fallback)
    return fallback


def shape_bounds(shape: ET.Element) -> dict[str, float | None]:
    xfrm = shape.find("p:spPr/a:xfrm", NS)
    ext = xfrm.find("a:ext", NS) if xfrm is not None else None
    off = xfrm.find("a:off", NS) if xfrm is not None else None
    return {
        "left_points": emu_to_points(off.attrib.get("x")) if off is not None else None,
        "top_points": emu_to_points(off.attrib.get("y")) if off is not None else None,
        "width_points": emu_to_points(ext.attrib.get("cx")) if ext is not None else None,
        "height_points": emu_to_points(ext.attrib.get("cy")) if ext is not None else None,
    }


def text_runs(shape: ET.Element) -> list[str]:
    return [
        text.strip()
        for text in (node.text for node in shape.findall(".//a:t", NS))
        if text and text.strip()
    ]


def max_font_size(shape: ET.Element, default: float = 18.0) -> float:
    sizes: list[float] = []
    for node in shape.findall(".//a:rPr", NS) + shape.findall(".//a:defRPr", NS):
        value = node.attrib.get("sz")
        if value:
            try:
                sizes.append(int(value) / 100.0)
            except ValueError:
                pass
    return max(sizes) if sizes else default


def paragraph_count(shape: ET.Element) -> int:
    count = len(shape.findall(".//a:p", NS))
    return max(count, 1)


def estimate_capacity(width_points: float, height_points: float, font_points: float) -> dict[str, int]:
    usable_width = max(width_points - 12.0, 1.0)
    usable_height = max(height_points - 8.0, 1.0)
    chars_per_line = max(int(usable_width / max(font_points * 0.52, 1.0)), 1)
    lines = max(int(usable_height / max(font_points * 1.22, 1.0)), 1)
    return {
        "estimated_chars_per_line": chars_per_line,
        "estimated_line_capacity": lines,
        "estimated_character_capacity": chars_per_line * lines,
    }


def classify_risk(character_count: int, paragraph_total: int, capacity: dict[str, int]) -> str:
    char_capacity = max(capacity["estimated_character_capacity"], 1)
    line_capacity = max(capacity["estimated_line_capacity"], 1)
    explicit_lines = max(paragraph_total, math.ceil(character_count / max(capacity["estimated_chars_per_line"], 1)))
    density = character_count / char_capacity
    line_pressure = explicit_lines / line_capacity
    if density >= 1.25 or line_pressure >= 1.4:
        return "high"
    if density >= 0.9 or line_pressure >= 1.0:
        return "medium"
    if density >= 0.7:
        return "low"
    return "none"


def inspect_shape(shape: ET.Element, index: int) -> dict | None:
    runs = text_runs(shape)
    if not runs:
        return None
    bounds = shape_bounds(shape)
    width = bounds["width_points"]
    height = bounds["height_points"]
    text = " ".join(runs)
    font = max_font_size(shape)
    if width is None or height is None:
        return {
            "shape_index": index,
            "shape_name": shape_name(shape, f"shape-{index}"),
            "risk": "unknown",
            "reason": "missing static shape bounds",
            "character_count": len(text),
            "font_points": font,
            **bounds,
        }
    capacity = estimate_capacity(width, height, font)
    risk = classify_risk(len(text), paragraph_count(shape), capacity)
    return {
        "shape_index": index,
        "shape_name": shape_name(shape, f"shape-{index}"),
        "risk": risk,
        "character_count": len(text),
        "paragraph_count": paragraph_count(shape),
        "font_points": font,
        **bounds,
        **capacity,
    }


def inspect_slide(archive: zipfile.ZipFile, slide_part: str, slide_index: int) -> dict:
    root = read_xml(archive, slide_part)
    if root is None:
        return {"index": slide_index, "part": slide_part, "risks": []}
    risks = []
    for index, shape in enumerate(root.findall(".//p:sp", NS), start=1):
        item = inspect_shape(shape, index)
        if item is not None and item["risk"] != "none":
            risks.append(item)
    return {
        "index": slide_index,
        "part": slide_part,
        "risks": risks,
    }


def risk_rank(value: str) -> int:
    return {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "unknown": 1,
    }.get(value, 0)


def inspect_pptx(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        slides = ordered_slides(archive)
        slide_reports = [inspect_slide(archive, slide_part, index + 1) for index, slide_part in enumerate(slides)]
    all_risks = [risk for slide in slide_reports for risk in slide["risks"]]
    highest = max((risk_rank(risk["risk"]) for risk in all_risks), default=0)
    severity = {0: "none", 1: "low", 2: "medium", 3: "high"}[highest]
    return {
        "source_path": str(path),
        "note": "Static OOXML text-density heuristic. True text bounds require PowerPoint COM rendering.",
        "highest_risk": severity,
        "risk_count": len(all_risks),
        "slides": slide_reports,
    }


def to_markdown(report: dict) -> str:
    lines = [
        "# Static Text Overflow Risk",
        "",
        f"- Source: `{report['source_path']}`",
        f"- Highest risk: `{report['highest_risk']}`",
        f"- Risk count: {report['risk_count']}",
        f"- Note: {report['note']}",
        "",
    ]
    for slide in report["slides"]:
        if not slide["risks"]:
            continue
        lines.extend([f"## Slide {slide['index']}", ""])
        lines.append("| Shape | Risk | Chars | Font pt | Box pt | Estimate |")
        lines.append("| --- | --- | ---: | ---: | --- | --- |")
        for risk in slide["risks"]:
            box = "{:.1f} x {:.1f}".format(risk.get("width_points") or 0, risk.get("height_points") or 0)
            estimate = "{} chars / {} lines".format(
                risk.get("estimated_character_capacity", "?"),
                risk.get("estimated_line_capacity", "?"),
            )
            lines.append(
                "| {shape_name} | `{risk}` | {character_count} | {font_points:.1f} | {box} | {estimate} |".format(
                    box=box,
                    estimate=estimate,
                    **risk,
                )
            )
        lines.append("")
    if report["risk_count"] == 0:
        lines.append("No static text-density risks detected.")
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
    parser = argparse.ArgumentParser(description="Flag static text-density risk in a .pptx without launching PowerPoint.")
    parser.add_argument("input", help="Path to the .pptx file")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", help="Optional output path")
    parser.add_argument(
        "--fail-on-risk",
        choices=("low", "medium", "high"),
        help="Exit 1 if the highest risk is at least this severity.",
    )
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

    if args.fail_on_risk and risk_rank(report["highest_risk"]) >= risk_rank(args.fail_on_risk):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
