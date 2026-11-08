"""
Overlay custom y-axis labels for precision/recall panels on Ultralytics results.png.

This does not change plotted curves; it only draws readable axis labels
with target values for Drowning and Swimming on the left side of the two
panels in the top row (metrics/precision(B), metrics/recall(B)).

Usage:
    python tools/update_results_axis.py --image mambayolo18/results.png 
        --precision_drowning 0.93 --precision_swimming 0.90 
        --recall_drowning 0.95 --recall_swimming 0.87

Output:
    Saves alongside the input as results_axis_updated.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def panel_box(W: int, H: int, row: int, col: int) -> tuple[int, int, int, int]:
    """Approximate bounding box (x0, y0, x1, y1) for a 2x5 grid layout."""
    # The standard results.png has consistent margins; we model them roughly.
    top_margin = int(0.06 * H)
    left_margin = int(0.06 * W)
    h_gap = int(0.03 * W)
    v_gap = int(0.06 * H)

    # Cell size derived from remaining space
    cell_w = (W - left_margin * 2 - h_gap * 4) // 5
    cell_h = (H - top_margin * 2 - v_gap) // 2

    x0 = left_margin + col * (cell_w + h_gap)
    y0 = top_margin + row * (cell_h + v_gap)
    x1 = x0 + cell_w
    y1 = y0 + cell_h
    return x0, y0, x1, y1


def overlay_axis_labels(im: Image.Image, box: tuple[int, int, int, int], lines: list[str]) -> None:
    """Draw a semi-transparent strip on left side and place multiple lines of text."""
    draw = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    strip_w = int((x1 - x0) * 0.18)
    strip_box = (x0, y0, x0 + strip_w, y1)

    overlay = Image.new("RGBA", (strip_w, y1 - y0), (255, 255, 255, 210))
    im.paste(overlay, (x0, y0), overlay)

    font = load_font(size=max(int((y1 - y0) * 0.11), 12))
    # Place texts evenly spaced
    step = (y1 - y0) // (len(lines) + 1)
    for i, text in enumerate(lines, start=1):
        tx = x0 + int(strip_w * 0.07)
        ty = y0 + i * step - int(step * 0.4)
        draw.text((tx, ty), text, fill=(0, 0, 0), font=font)


def main():
    ap = argparse.ArgumentParser(description="Overlay axis labels for precision/recall panels")
    ap.add_argument("--image", required=True, type=str)
    ap.add_argument("--precision_drowning", required=True, type=float)
    ap.add_argument("--precision_swimming", required=True, type=float)
    ap.add_argument("--recall_drowning", required=True, type=float)
    ap.add_argument("--recall_swimming", required=True, type=float)
    args = ap.parse_args()

    img_path = Path(args.image)
    if not img_path.exists():
        raise FileNotFoundError(img_path)

    im = Image.open(img_path).convert("RGBA")
    W, H = im.size

    # Top row col=3 => metrics/precision(B); col=4 => metrics/recall(B)
    precision_box = panel_box(W, H, row=0, col=3)
    recall_box = panel_box(W, H, row=0, col=4)

    overlay_axis_labels(
        im,
        precision_box,
        [f"Drowning {args.precision_drowning:.2f}", f"Swimming {args.precision_swimming:.2f}"],
    )
    overlay_axis_labels(
        im,
        recall_box,
        [f"Drowning {args.recall_drowning:.2f}", f"Swimming {args.recall_swimming:.2f}"],
    )

    out_path = img_path.with_name(img_path.stem + "_axis_updated" + img_path.suffix)
    im.convert("RGB").save(out_path)
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()

