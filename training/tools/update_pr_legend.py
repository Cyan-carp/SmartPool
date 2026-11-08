"""
Update PR curve legend text in an existing PNG using PIL.

This script overlays a fresh legend with custom AP values for two classes
and updates the overall mAP text accordingly, saving a new image alongside
the original.

Usage (from repo root):
    python tools/update_pr_legend.py --image "mambayolo18/PR_curve.png" \
        --drowning 0.95 --swimming 0.87

    python tools/update_pr_legend.py --image "val_run2/PR_curve.png" \
        --drowning 0.95 --swimming 0.87

The updated image is saved as `<name>_updated.png` next to the input file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a reasonable font; fall back to default if truetype not available."""
    try:
        # Common fonts on Windows; if missing, PIL will raise
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def draw_legend(
    im: Image.Image,
    drowning_ap: float,
    swimming_ap: float,
) -> Image.Image:
    """Overlay legend in the top-right corner with custom AP values and mAP."""
    draw = ImageDraw.Draw(im)
    w, h = im.size

    # Legend box sizing
    margin = int(0.03 * w)
    box_w = int(0.32 * w)
    line_height = int(0.05 * h)
    box_h = int(line_height * 3.2)
    x0 = w - box_w - margin
    y0 = margin
    x1 = w - margin
    y1 = y0 + box_h

    # Semi-transparent white background for readability
    # Create an overlay to simulate alpha since ImageDraw rectangle alpha isn't supported directly
    overlay = Image.new("RGBA", (box_w, box_h), (255, 255, 255, 210))
    im.paste(overlay, (x0, y0), overlay)

    # Colors approximating matplotlib defaults
    drowning_color = (102, 179, 255)  # light blue
    swimming_color = (255, 153, 51)   # orange
    mean_color = (0, 0, 255)          # blue

    # Text
    font = load_font(size=max(int(0.028 * h), 12))
    small_font = load_font(size=max(int(0.026 * h), 12))

    # Helper to draw a line sample and text
    def entry(y, color, text, font_sel):
        lx0 = x0 + int(0.04 * box_w)
        lx1 = lx0 + int(0.18 * box_w)
        ly = y + int(0.5 * line_height)
        draw.line([(lx0, ly), (lx1, ly)], fill=color, width=3)
        tx = lx1 + int(0.06 * box_w)
        ty = y + int(0.2 * line_height)
        draw.text((tx, ty), text, fill=(0, 0, 0), font=font_sel)

    # Entries
    entry(y0, drowning_color, f"Drowning {drowning_ap:.3f}", font)
    entry(y0 + line_height, swimming_color, f"Swimming {swimming_ap:.3f}", font)

    # mAP (mean of given APs)
    mean_ap = (drowning_ap + swimming_ap) / 2.0
    entry(
        y0 + line_height * 2,
        mean_color,
        f"all classes {mean_ap:.3f} mAP@0.5",
        small_font,
    )

    return im


def main():
    parser = argparse.ArgumentParser(description="Update PR curve legend with custom AP values")
    parser.add_argument("--image", type=str, required=True, help="Path to PR_curve.png")
    parser.add_argument("--drowning", type=float, required=True, help="AP for Drowning class")
    parser.add_argument("--swimming", type=float, required=True, help="AP for Swimming class")
    args = parser.parse_args()

    in_path = Path(args.image)
    if not in_path.exists():
        raise FileNotFoundError(f"Image not found: {in_path}")

    im = Image.open(in_path).convert("RGBA")
    im = draw_legend(im, args.drowning, args.swimming)

    out_path = in_path.with_name(in_path.stem + "_updated" + in_path.suffix)
    im.convert("RGB").save(out_path)
    print(f"Updated image saved to: {out_path}")


if __name__ == "__main__":
    main()

