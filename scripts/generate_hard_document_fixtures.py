from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
import textwrap

import fitz
from PIL import Image, ImageDraw, ImageFont


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = WORKSPACE_ROOT / "temp" / "hard-document-fixtures"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _font(size: int, *, handwritten: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            Path("C:/Windows/Fonts/comic.ttf"),
            Path("C:/Windows/Fonts/segoepr.ttf"),
            Path("C:/Windows/Fonts/Inkfree.ttf"),
        ]
        if handwritten
        else []
    )
    names = ["DejaVuSans-Oblique.ttf"] if handwritten else ["DejaVuSans.ttf"]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_wrapped_lines(
    image: Image.Image,
    lines: list[str],
    *,
    origin: tuple[int, int] = (110, 110),
    width: int = 58,
    font_size: int = 42,
    handwritten: bool = False,
    extra_word_spacing: int = 0,
) -> None:
    draw = ImageDraw.Draw(image)
    font = _font(font_size, handwritten=handwritten)
    x, y = origin
    line_height = font_size + 22
    for paragraph in lines:
        for line in textwrap.wrap(paragraph, width=width) or [""]:
            if extra_word_spacing <= 0:
                draw.text((x, y), line, fill=(25, 30, 34), font=font)
            else:
                cursor = float(x)
                for word in line.split():
                    draw.text((cursor, y), word, fill=(25, 30, 34), font=font)
                    cursor += float(draw.textlength(word, font=font)) + extra_word_spacing
            y += line_height
        y += 24


def _insert_page_text(page: fitz.Page, title: str, paragraphs: list[str]) -> None:
    page.insert_text((54, 58), title, fontsize=20, fontname="helv", color=(0.04, 0.2, 0.2))
    y = 92
    for paragraph in paragraphs:
        used = page.insert_textbox(
            fitz.Rect(54, y, 540, y + 150),
            paragraph,
            fontsize=11.5,
            fontname="helv",
            lineheight=1.35,
            color=(0.08, 0.09, 0.1),
        )
        y += max(70, 155 - max(used, 0))


def _make_diagram(path: Path) -> None:
    image = Image.new("RGB", (1200, 500), (246, 249, 247))
    draw = ImageDraw.Draw(image)
    font = _font(34)
    labels = ["Sensor", "Comparator", "Controller", "Actuator"]
    boxes: list[tuple[int, int, int, int]] = []
    for index, label in enumerate(labels):
        x = 55 + (index * 285)
        box = (x, 165, x + 210, 285)
        boxes.append(box)
        draw.rounded_rectangle(box, radius=18, outline=(14, 102, 88), width=6, fill=(229, 242, 237))
        bounds = draw.textbbox((0, 0), label, font=font)
        text_width = bounds[2] - bounds[0]
        draw.text((x + ((210 - text_width) / 2), 205), label, font=font, fill=(20, 44, 41))
    for left, right in zip(boxes, boxes[1:]):
        y = 225
        draw.line((left[2] + 8, y, right[0] - 18, y), fill=(22, 108, 96), width=7)
        draw.polygon(
            [(right[0] - 18, y - 13), (right[0] - 18, y + 13), (right[0], y)],
            fill=(22, 108, 96),
        )
    draw.text((55, 54), "Closed-loop feedback chain", font=_font(46), fill=(10, 67, 61))
    image.save(path)


def _make_textbook_pdf(path: Path, diagram_path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    _insert_page_text(
        page,
        "Chapter 1 - Adaptive Measurement",
        [
            "Adaptive sampling changes the measurement interval according to signal variation. "
            "Rapidly changing signals are sampled more often, while stable signals are sampled less often.",
            "The method reduces redundant measurements without ignoring short-lived changes. A valid controller "
            "therefore observes variation before changing the interval.",
        ],
    )

    page = document.new_page(width=595, height=842)
    _insert_page_text(
        page,
        "Chapter 2 - Stability Margin",
        [
            "The stability margin is calculated as M = (target - measured) / max(abs(target), epsilon).",
            "A positive margin means the measured value remains below the target. A negative margin means the "
            "measurement has crossed the target. Epsilon prevents division by zero.",
        ],
    )

    page = document.new_page(width=595, height=842)
    _insert_page_text(
        page,
        "Chapter 3 - Drift Response Table",
        [
            "The drift policy uses two operational bands.",
            "Low drift | below 0.5 percent per hour | monitor normally.",
            "High drift | above 2.0 percent per hour | recalibrate immediately.",
            "Values between the two bands require a second observation before changing the calibration.",
        ],
    )
    page.draw_line((54, 245), (540, 245), color=(0.1, 0.35, 0.32), width=1.2)
    page.draw_line((54, 300), (540, 300), color=(0.1, 0.35, 0.32), width=1.2)

    page = document.new_page(width=595, height=842)
    page.insert_text((54, 58), "Chapter 4 - Feedback Diagram", fontsize=20, fontname="helv")
    page.insert_image(fitz.Rect(54, 105, 540, 310), filename=str(diagram_path))
    page.insert_textbox(
        fitz.Rect(54, 335, 540, 430),
        "Figure 1 shows the feedback chain: sensor, comparator, controller, and actuator. "
        "The comparator measures error before the controller selects a correction.",
        fontsize=11.5,
        fontname="helv",
        lineheight=1.35,
    )
    document.save(path, garbage=4, deflate=True, no_new_id=True)
    document.close()


def _add_scan_noise(image: Image.Image, *, seed: int) -> None:
    rng = random.Random(seed)
    draw = ImageDraw.Draw(image)
    for _ in range(1400):
        x = rng.randrange(image.width)
        y = rng.randrange(image.height)
        shade = rng.randrange(205, 238)
        draw.point((x, y), fill=(shade, shade, shade))


def _make_scanned_pdf(path: Path) -> None:
    pages: list[Image.Image] = []
    content = [
        [
            "SCANNED SIGNAL PROCESSING NOTES",
            "Spectral leakage spreads energy into neighboring frequency bins when the observation window does not contain an integer number of cycles.",
            "A tapered window reduces leakage but also widens the main lobe.",
        ],
        [
            "CALIBRATION PROCEDURE",
            "First remove sensor bias, then collect three reference readings, and finally store the median correction.",
            "Frequency resolution equals sample rate divided by sample count.",
        ],
    ]
    for index, lines in enumerate(content):
        image = Image.new("RGB", (1700, 2200), (248, 246, 239))
        _draw_wrapped_lines(image, lines, width=57, font_size=42, extra_word_spacing=13)
        _add_scan_noise(image, seed=4100 + index)
        pages.append(image.rotate(0.35 if index == 0 else -0.25, expand=False, fillcolor=(248, 246, 239)))

    document = fitz.open()
    for image in pages:
        page = document.new_page(width=595, height=770)
        image_bytes = _image_bytes(image)
        page.insert_image(page.rect, stream=image_bytes)
    document.save(path, garbage=4, deflate=True, no_new_id=True)
    document.close()


def _image_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _make_handwritten_note(path: Path) -> None:
    image = Image.new("RGB", (1700, 1200), (250, 247, 232))
    draw = ImageDraw.Draw(image)
    for y in range(150, 1120, 90):
        draw.line((70, y, 1630, y), fill=(192, 215, 224), width=2)
    _draw_wrapped_lines(
        image,
        [
            "Lab note: Before measuring thermal response, zero the probe and wait two minutes for the reference bath to stabilize.",
            "If the trace oscillates, reduce controller gain before repeating the test.",
        ],
        origin=(105, 120),
        width=52,
        font_size=48,
        handwritten=True,
        extra_word_spacing=8,
    )
    image.save(path)


def generate_fixtures(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagram = output_dir / "feedback_chain.png"
    textbook = output_dir / "nirmiq_hard_textbook.pdf"
    scanned = output_dir / "nirmiq_scanned_notes.pdf"
    handwritten = output_dir / "nirmiq_handwritten_note.png"

    _make_diagram(diagram)
    _make_textbook_pdf(textbook, diagram)
    _make_scanned_pdf(scanned)
    _make_handwritten_note(handwritten)

    manifest = {
        "version": "hard-documents-v1",
        "fixtures": {
            "textbook": str(textbook),
            "scan": str(scanned),
            "handwritten": str(handwritten),
            "diagram_source": str(diagram),
        },
        "sha256": {
            "textbook": _sha256(textbook),
            "scan": _sha256(scanned),
            "handwritten": _sha256(handwritten),
            "diagram_source": _sha256(diagram),
        },
        "coverage": [
            "additional textbook-like source",
            "equation",
            "table",
            "embedded diagram",
            "raster-only scan",
            "handwritten-style image note",
        ],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate original NIRMIQ hard-document fixtures.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = generate_fixtures(args.output_dir.resolve())
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
